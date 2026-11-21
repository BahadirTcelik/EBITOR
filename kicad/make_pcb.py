"""Generate the first board file (placement only, no routing) from the schematic netlist.

    python make_pcb.py            writes ee463_dcdc.kicad_pcb next to this file and prints the placement checks
    python make_pcb.py --force    the same, even if the board file was changed after the last run of this script

Steps: export the netlist of ee463_dcdc.kicad_sch with kicad-cli, load every footprint and net from it (the same
result as "Update PCB from Schematic"), set a 4-layer board with a rounded 100 x 70 mm outline, place all parts
from the table PLACE below, draw draft copper zones and the silkscreen texts, fill the zones and measure the
distances that the course PCB-Checker looks at.

Needs KiCad's Python module (pcbnew). Written and run with KiCad 7.0.11; KiCad 8-10 open the file.
Regenerating OVERWRITES ee463_dcdc.kicad_pcb. The script stores the hash of the file it wrote in
out/pcb_generated.sha256 and stops if the board on disk is different (edited or saved in KiCad), unless --force is given.
"""
import hashlib
import math
import os
import re
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "netlist"))
import schematic_netlist as NL  # noqa: E402  (MPN, DNP and assembly group of every part; also rewrites pins.csv and the BOM)

DNP_REFS = set()


def parse(text):
    """Minimal s-expression reader for the KiCad netlist."""
    stack, cur = [], []
    for m in re.finditer(r'\(|\)|"((?:[^"\\]|\\.)*)"|[^\s()"]+', text):
        t = m.group(0)
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done, cur = cur, stack.pop()
            cur.append(done)
        else:
            cur.append(m.group(1) if t.startswith('"') else t)
    return cur[0]


def child(e, name):
    return [x for x in e if isinstance(x, list) and x and x[0] == name]

PROJECT = "ee463_dcdc"
PCB = os.path.join(HERE, PROJECT + ".kicad_pcb")
K7_COPY = os.path.join(HERE, "out", PROJECT + "_k7.kicad_pcb")      # same board without the DNP flags (readable by KiCad 7)
SCH = os.path.join(HERE, PROJECT + ".kicad_sch")
FPDIR = os.environ.get("KICAD_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
OX, OY = 50.0, 40.0            # board origin on the sheet (mm)
W, H, RAD = 100.0, 70.0, 3.0   # board outline and corner radius (mm)
EDGE_INSET = 0.7               # copper pours stay this far from the board edge (rule: 0.5 mm)
mm, fmm = pcbnew.ToMM, pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(fmm(OX + x), fmm(OY + y))


# ----------------------------------------------------------------------------- placement table (board mm, degrees)
# KiCad angles are counter-clockwise on screen: a pad at local (x, y) lands at (y, -x) for 90 and (-y, x) for 270.
A, B, C_ = 32.6, 44.7, 48.9          # y of the rows above U1 (A) and below it (B, C_)
PLACE = {
    # input, reverse polarity
    "J1": (6, 17, 90), "Q3": (16, 6.3, 180), "R2": (13.5, 14.3, 270), "R3": (17.6, 14.3, 270),
    "C1": (22.5, 4.4, 0), "D3": (23.0, 7.4, 0), "R1": (28, 8.3, 90),
    "C8": (15.5, 24.5, 270), "R4": (15.5, 36.2, 0),
    "C2": (48.5, 17.9, 0), "C3": (48.5, 14.6, 0),
    "C4": (39, 27.6, 270), "C5": (35.5, 27.6, 270), "C6": (32, 27.6, 270), "C7": (28.5, 27.6, 270),
    "R21": (23.4, 30.3, 270), "R9": (25.8, 30.3, 270),
    # power stage
    "Q1": (44.5, 24, 90), "Q2": (52.5, 24, 270), "L1": (69.5, 28.2, 0), "RS1": (83.5, 28.2, 0),
    "R7": (57.0, 23.3, 90), "C15": (57.0, 19.0, 90),
    "C9": (91.7, 21.5, 0), "C10": (91.7, 24.8, 0), "C11": (91.7, 28.1, 0), "C12": (91.7, 31.4, 0),
    "C13": (91.1, 37.5, 0), "C14": (80, 43.2, 180),
    "RSH1": (86.5, 50, 270), "J2": (93, 53, 270),
    # controller: row A between the MOSFETs and U1
    "U1": (47, 38.7, 90),
    "R22": (33.8, A, 90), "C16": (38.6, A, 90), "C25": (41.0, A, 90), "C27": (43.4, A, 90), "C26": (45.8, A, 90),
    "C24": (48.2, A, 90), "R6": (50.6, A, 90), "C22": (53.0, A, 90), "R5": (55.4, A, 90),
    "R10": (40.2, 38.7, 270), "C23": (37.6, 38.7, 90),
    # rows B and C below U1 (small-signal side, away from SW)
    "C17": (37.8, B, 270), "R11": (40.2, B, 270), "C21": (42.6, B, 270), "R14": (45.0, B, 270), "R13": (47.4, B, 90),
    "C20": (49.8, B, 270), "R8": (52.2, B, 270), "R19": (54.6, B, 270), "R17": (57.0, B, 270),
    "R12": (37.8, C_, 90), "R20": (40.2, C_, 90), "R18": (42.6, C_, 270), "C18": (45.0, C_, 90), "R15": (47.4, C_, 90),
    "R16": (49.8, C_, 270), "C19": (52.2, C_, 90), "R25": (54.6, C_, 270),      # R25: CC link, stays at the ITH pin
    # assembly group B: current-limit (CC) circuit, one block beside the shunt at the lower board edge (frame CC_FRAME).
    # Signal flow right to left: RSH1 -> U2 -> R23 -> U3 (integrator C30, clamp D2) -> D1 -> R24 -> CC_LINK -> R25 at U1.
    "U2": (80.6, 50.8, 180), "C28": (76.8, 51.75, 180), "C29": (73.14, 51.55, 90),
    "R24": (62.4, 54.05, 0), "D1": (66.6, 54.05, 180), "U3": (72.0, 55.0, 0), "R23": (76.2, 55.95, 180),
    "C31": (67.6, 56.3, 180), "C30": (72.5, 58.2, 180), "D2": (72.0, 60.5, 180),
    # 5 V rail: R29 from DRVCC, TL431 U4 with R26 / R30, rail capacitor C33
    "C33": (77.1, 58.2, 180), "R29": (81.2, 58.2, 180), "U4": (78.6, 61.2, 0), "R26": (75.4, 61.3, 270), "R30": (77.0, 64.6, 0),
    # threshold divider and trimmer
    "R28": (61.4, 60.4, 0), "R27": (67.9, 60.4, 0), "RV1": (65.6, 65.3, 0),
    # HT7550 variant only (CC_SUPPLY = "HT7550_LDO" in the netlist): not placed in this layout
    # test points
    "TP1": (36, 6, 0), "TP2": (10.6, 6.0, 0), "TP3": (62, 8, 0), "TP6": (86.0, 58.0, 0), "TP7": (88.6, 43.95, 0),
    "TP8": (57.3, 28.1, 0), "TP9": (61.5, 41.2, 0), "TP10": (65.8, 41.2, 0),
    "TP4": (12, 65.5, 0), "TP11": (16.5, 65.5, 0), "TP12": (21, 65.5, 0), "TP13": (25.5, 65.5, 0), "TP16": (30, 65.5, 0),
    "TP15": (34.5, 65.5, 0), "TP17": (39, 65.5, 0), "TP14": (43.5, 65.5, 0), "TP5": (88.0, 65.5, 0),
    # group B test points: one column in the left part of the CC block, labels to the right
    "TP19": (48.4, 55.7, 0), "TP20": (48.4, 59.4, 0), "TP18": (48.4, 63.1, 0), "TP21": (48.4, 66.8, 0),
    # mounting holes: 4.5 mm from the edges
    "H1": (4.5, 4.5, 0), "H2": (95.5, 4.5, 0), "H3": (4.5, 65.5, 0), "H4": (95.5, 65.5, 0),
}
ROW_TP = {"TP4", "TP11", "TP12", "TP13", "TP16", "TP15", "TP17", "TP14", "TP5"}
# outline of the CC block on the silkscreen (board mm) and its title
CC_FRAME = [(59.6, 48.3), (83.0, 48.3), (83.0, 68.8), (46.0, 68.8), (46.0, 52.2), (59.6, 52.2)]
CC_TITLE = ("CC (opsiyonel)", 46.8, 53.5, 1.1)

# Silkscreen references. Chip parts (0805, 1206, 1210) get no reference on the silkscreen: at 2.4 mm pitch there is
# no room for 1.0 mm text. Their references are on F.Fab (out/assembly_top.pdf). Larger parts: position (x, y, angle).
REF_POS = {
    "J1": (2.6, 8.2, 0), "J2": (89.9, 62.0, 0), "D3": (23.0, 9.4, 0), "Q2": (53.5, 19.6, 0), "R2": (13.5, 14.3, 90),
    "R3": (17.6, 14.3, 90), "R4": (15.5, 39.0, 0), "RSH1": (83.9, 50.0, 90), "U1": (53.6, 38.7, 0),
    "C13": (97.3, 37.5, 90), "C14": (73.7, 42.5, 90),
    "U2": (77.5, 49.3, 0), "U3": (69.0, 51.6, 0), "U4": (81.6, 61.2, 0), "D1": (66.6, 51.9, 0), "D2": (68.2, 58.5, 0),
    "RV1": (64.65, 60.4, 0),
}

# test point labels that do not fit above the loop: (dx, dy, justification)
LEFT = pcbnew.GR_TEXT_H_ALIGN_LEFT
TP_LABEL = {"TP2": (-1.0, -2.4, None), "TP8": (0, 2.3, None), "TP7": (2.2, 0, LEFT),
            "TP18": (2.3, 0, LEFT), "TP19": (2.3, 0, LEFT), "TP20": (2.3, 0, LEFT), "TP21": (2.3, 0, LEFT)}

# draft copper zones: (net, layer, priority, clearance mm, solid pad connection, polygon in board mm)
VIN_X1 = 78.0      # right end of the VIN pour strip along the top edge (extended on 17 Nov to reach 10 cm2 on L1)
ZONES = [
    ("VIN", "F.Cu", 2, 0.5, True, [(2.6, 14.9), (10.9, 14.9), (10.9, 19.4), (26, 19.4), (26, 8.4), (31, 8.4), (31, 2.4),
                                   (VIN_X1, 2.4), (VIN_X1, 12.4), (47.9, 12.4), (47.9, 25.5), (42.2, 25.5), (42.2, 27.75), (26.7, 27.75), (26.7, 29.95),
                                   (22.5, 29.95), (22.5, 27.75), (2.6, 27.75)]),
    ("VIN_RTN", "F.Cu", 2, 0.5, True, [(2.6, 9.6), (8.6, 9.6), (8.6, 2.4), (17.5, 2.4), (17.5, 9.6), (19.6, 9.6),
                                       (19.6, 12.3), (10.9, 12.3), (10.9, 13.9), (2.6, 13.9)]),
    ("SW", "F.Cu", 2, 0.5, True, [(41.9, 26.3), (45.75, 26.3), (45.75, 27.7), (50.1, 27.7), (50.1, 22.6), (54.9, 22.6),
                                  (54.9, 24.0), (58.2, 24.0), (58.2, 25.0), (65.9, 25.0), (65.9, 31.4), (58.6, 31.4),
                                  (58.6, 29.8), (41.9, 29.8)]),
    ("SNS_P", "F.Cu", 2, 0.3, True, [(72.9, 25.0), (81.4, 25.0), (81.4, 31.4), (72.9, 31.4)]),
    ("VOUT_C", "F.Cu", 2, 0.3, True, [(84.6, 19.0), (91.2, 19.0), (91.2, 47.8), (84.6, 47.8), (84.6, 44.8), (80.8, 44.8),
                                      (80.8, 41.6), (84.6, 41.6)]),
    ("VOUT", "F.Cu", 2, 0.3, True, [(84.0, 52.0), (95.0, 52.0), (95.0, 54.6), (88.6, 54.6), (88.6, 59.8), (84.0, 59.8)]),
    ("GND", "F.Cu", 0, 0.3, False, "board"),
    ("GND", "In1.Cu", 0, 0.3, False, "board"),          # L2: unbroken ground plane
    ("GND", "B.Cu", 0, 0.3, False, "board"),
    # second copper on L4: so far connected only through the VIN and VOUT_C test point pins; the stitching
    # vias next to Q1 and the output capacitors are placed in the routing step
    ("VIN", "B.Cu", 2, 0.5, True, [(26, 2.4), (VIN_X1, 2.4), (VIN_X1, 12.4), (47.9, 12.4), (47.9, 25.5), (26, 25.5)]),
    ("VOUT_C", "B.Cu", 2, 0.3, True, [(84.6, 19.0), (91.2, 19.0), (91.2, 47.8), (84.6, 47.8)]),
]
SILK = [  # text, x, y, angle, size
    ("EE463 60 W BUCK", 3.5, 43.0, 0, 2.0), ("20-48V IN  12V 5A OUT", 3.5, 46.6, 0, 1.3),
    ("GROUP __   REV A   2026-11", 3.5, 49.8, 0, 1.2),
    ("IN 20-48V", 1.6, 23.6, 0, 1.0), ("+", 5.4, 21.4, 0, 1.5), ("-", 5.4, 8.2, 0, 1.5),
    ("OUT 12V", 91.6, 46.9, 0, 1.0), ("+", 92.4, 48.9, 0, 1.5), ("-", 92.4, 62.0, 0, 1.5),
]


# ----------------------------------------------------------------------------- netlist -> board
def read_netlist():
    net_file = os.path.join(HERE, "out", PROJECT + "_for_pcb.net")
    os.makedirs(os.path.dirname(net_file), exist_ok=True)
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net_file, SCH],
                   check=True, capture_output=True)
    with open(net_file, encoding="utf-8") as f:
        tree = parse(f.read())
    comps, nodes, pininfo = [], {}, {}
    for comp in child(child(tree, "components")[0], "comp"):
        comps.append(dict(ref=child(comp, "ref")[0][1], value=child(comp, "value")[0][1],
                          fp=child(comp, "footprint")[0][1], uuid=child(comp, "tstamps")[0][1]))
    for net in child(child(tree, "nets")[0], "net"):
        name = child(net, "name")[0][1]
        for node in child(net, "node"):
            key = (child(node, "ref")[0][1], child(node, "pin")[0][1])
            nodes[key] = name
            fn, ty = child(node, "pinfunction"), child(node, "pintype")
            pininfo[key] = (fn[0][1] if fn else "", ty[0][1] if ty else "")
    return comps, nodes, pininfo


def build():
    comps, nodes, pininfo = read_netlist()
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(fmm(1.6))
    ds.m_CopperEdgeClearance = fmm(0.5)
    ds.m_MinClearance = fmm(0.15)
    ds.m_TrackMinWidth = fmm(0.15)
    ds.m_MinThroughDrill = fmm(0.30)
    ds.m_ViasMinAnnularWidth = fmm(0.15)
    ds.m_ViasMinSize = fmm(0.60)
    ds.m_HoleClearance = fmm(0.25)
    ds.m_HoleToHoleMin = fmm(0.50)
    nets = {}

    def net(name):
        if name not in nets:
            nets[name] = pcbnew.NETINFO_ITEM(board, name)
            board.Add(nets[name])
        return nets[name]

    info = {x["ref"]: x for x in NL.C}                   # MPN, fitted / DNP, assembly group
    missing = [c["ref"] for c in comps if c["ref"] not in PLACE]
    if missing:
        raise SystemExit(f"no position for {missing}")
    for c in comps:
        lib, name = c["fp"].split(":")
        path = os.path.join(HERE, "ee463.pretty") if lib == "ee463" else os.path.join(FPDIR, lib + ".pretty")
        fp = pcbnew.FootprintLoad(path, name)
        if fp is None:
            raise SystemExit(f"footprint {c['fp']} not found")
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(c["ref"])
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))       # link to the schematic symbol, as F8 does
        fp.SetProperty("MPN", info[c["ref"]]["mpn"])        # the schematic symbols carry this field; KiCad 8+ compares it
        if not info[c["ref"]]["fit"]:
            DNP_REFS.add(c["ref"])                          # written into the file by mark_dnp(): pcbnew 7 has no DNP flag
        if not info[c["ref"]]["pins"]:
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM)
        board.Add(fp)
        for pad in fp.Pads():
            n = nodes.get((c["ref"], pad.GetNumber()))
            if n:
                pad.SetNet(net(n))
            fn, ty = pininfo.get((c["ref"], pad.GetNumber()), ("", ""))
            if fn:
                pad.SetPinFunction(fn)                    # same pad properties that "Update PCB from schematic" writes
            if ty:
                pad.SetPinType(ty)
            if c["ref"] == "U1" and n == "GND":             # exposed pad, its vias and the GND pins: solid, no thermal spokes
                pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        x, y, rot = PLACE[c["ref"]]
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        ref_text = fp.Reference()
        ref_text.SetTextSize(pcbnew.VECTOR2I(fmm(1.0), fmm(1.0)))
        ref_text.SetTextThickness(fmm(0.15))
        if c["ref"].startswith(("TP", "H")):
            ref_text.SetVisible(False)                   # the silkscreen carries the net name instead
        elif any(k in name for k in ("_0805_", "_1206_", "_1210_")):
            ref_text.SetVisible(False)                   # see REF_POS
        elif c["ref"] in REF_POS:
            rx, ry, ra = REF_POS[c["ref"]]
            ref_text.SetPosition(P(rx, ry))
            ref_text.SetTextAngleDegrees((ra - rot) % 360)   # pcbnew stores the angle relative to the footprint
            ref_text.SetKeepUpright(False)
    outline(board)
    silk(board, comps)
    zones(board, nets)
    return board, comps, nodes


def outline(board):
    def seg(x1, y1, x2, y2):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(x1, y1)); s.SetEnd(P(x2, y2))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(fmm(0.1))
        board.Add(s)

    def arc(cx, cy, a0):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        pts = [(cx + RAD * math.cos(math.radians(a)), cy + RAD * math.sin(math.radians(a))) for a in (a0, a0 + 45, a0 + 90)]
        s.SetArcGeometry(P(*pts[0]), P(*pts[1]), P(*pts[2]))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(fmm(0.1))
        board.Add(s)

    seg(RAD, 0, W - RAD, 0); seg(W, RAD, W, H - RAD); seg(W - RAD, H, RAD, H); seg(0, H - RAD, 0, RAD)
    arc(RAD, RAD, 180); arc(W - RAD, RAD, 270); arc(W - RAD, H - RAD, 0); arc(RAD, H - RAD, 90)


def text(board, s, x, y, angle=0, size=1.0, layer=pcbnew.F_SilkS, justify=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(fmm(size), fmm(size)))
    t.SetTextThickness(fmm(0.15 * size))
    t.SetTextAngleDegrees(angle)
    if justify is not None:
        t.SetHorizJustify(justify)
    board.Add(t)


def silk(board, comps):
    for s, x, y, a, size in SILK:
        text(board, s, x, y, a, size, justify=pcbnew.GR_TEXT_H_ALIGN_LEFT)
    for (x1, y1), (x2, y2) in zip(CC_FRAME, CC_FRAME[1:] + CC_FRAME[:1]):     # frame of assembly group B
        ln = pcbnew.PCB_SHAPE(board)
        ln.SetShape(pcbnew.SHAPE_T_SEGMENT)
        ln.SetStart(P(x1, y1)); ln.SetEnd(P(x2, y2))
        ln.SetLayer(pcbnew.F_SilkS); ln.SetWidth(fmm(0.15))
        board.Add(ln)
    text(board, CC_TITLE[0], CC_TITLE[1], CC_TITLE[2], 0, CC_TITLE[3], justify=pcbnew.GR_TEXT_H_ALIGN_LEFT)
    for c in comps:
        if not c["ref"].startswith("TP"):
            continue
        x, y, _ = PLACE[c["ref"]]
        if c["ref"] in ROW_TP:      # bottom row: vertical label above the loop
            text(board, c["value"], x, y - 1.9, 90, 1.0, justify=pcbnew.GR_TEXT_H_ALIGN_LEFT)
        elif c["ref"] in TP_LABEL:
            dx, dy, just = TP_LABEL[c["ref"]]
            text(board, c["value"], x + dx, y + dy, 0, 1.0, justify=just)
        else:                       # an underscore hangs below the baseline: keep it off the loop's circle
            text(board, c["value"], x, y - (2.4 if "_" in c["value"] else 2.1), 0, 1.0)


def zones(board, nets):
    for name, layer, prio, clr, solid, poly in ZONES:
        z = pcbnew.ZONE(board)
        z.SetLayer(board.GetLayerID(layer))
        z.SetNetCode(nets[name].GetNetCode())
        z.SetAssignedPriority(prio)
        z.SetLocalClearance(fmm(clr))
        z.SetMinThickness(fmm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(fmm(0.4)); z.SetThermalReliefSpokeWidth(fmm(0.6))
        if poly == "board":                               # board outline moved in by EDGE_INSET, corners included
            r, poly = RAD - EDGE_INSET, []
            for cx, cy, a0 in ((RAD, RAD, 180), (W - RAD, RAD, 270), (W - RAD, H - RAD, 0), (RAD, H - RAD, 90)):
                poly += [(cx + r * math.cos(math.radians(a0 + a)), cy + r * math.sin(math.radians(a0 + a)))
                         for a in range(0, 91, 10)]
        ol = z.Outline()
        ol.NewOutline()
        for x, y in poly:
            ol.Append(fmm(OX + x), fmm(OY + y))
        board.Add(z)


# ----------------------------------------------------------------------------- checks
def rect(pad):
    bb = pad.GetBoundingBox()
    return (mm(bb.GetLeft()) - OX, mm(bb.GetTop()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY)


def gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)


def checks(board, nodes):
    fps = {f.GetReference(): f for f in board.GetFootprints()}

    def pads(ref, pins=None, netname=None):
        out = []
        for p in fps[ref].Pads():
            if not p.GetNumber() or not p.IsOnLayer(pcbnew.F_Cu):
                continue
            if pins is not None and p.GetNumber() not in pins:
                continue
            if netname is not None and p.GetNetname() != netname:
                continue
            out.append(p)
        return out

    def edge(ref_a, sel_a, ref_b, sel_b):
        return min(gap(rect(a), rect(b)) for a in pads(ref_a, **sel_a) for b in pads(ref_b, **sel_b))

    def centre(ref_a, pin_a, ref_b, pin_b):
        a, b = pads(ref_a, [pin_a])[0].GetPosition(), pads(ref_b, [pin_b])[0].GetPosition()
        return mm(math.hypot(a.x - b.x, a.y - b.y))

    rows = []

    def add(what, value, limit, kind="max"):
        ok = value <= limit if kind == "max" else value >= limit
        rows.append((what, value, ("<= " if kind == "max" else ">= ") + f"{limit:g}", "ok" if ok else "FAIL"))

    for cap in ("C2", "C3"):
        add(f"{cap} VIN pad to Q1 drain pad (edge)", edge(cap, dict(netname="VIN"), "Q1", dict(pins=["5"])), 5)
        add(f"{cap} GND pad to Q2 source pads (edge)", edge(cap, dict(netname="GND"), "Q2", dict(pins=["1", "2", "3"])), 5)
    add("U1 TG pin 20 to Q1 gate pad (centres)", centre("U1", "20", "Q1", "4"), 15)
    add("U1 BG pin 24 to Q2 gate pad (centres)", centre("U1", "24", "Q2", "4"), 15)
    add("C22 to U1 BOOST pin 22 (edge)", edge("C22", dict(netname="BOOST"), "U1", dict(pins=["22"])), 5)
    add("C22 to U1 SW pin 21 (edge)", edge("C22", dict(netname="SW"), "U1", dict(pins=["21"])), 5)
    add("R13 to U1 VFB pin 6 (edge)", edge("R13", dict(netname="VFB"), "U1", dict(pins=["6"])), 10)
    add("R14 to U1 VFB pin 6 (edge)", edge("R14", dict(netname="VFB"), "U1", dict(pins=["6"])), 10)
    for cap, netname, ic, pin in (("C24", "DRVCC", "U1", "26"), ("C25", "INTVCC", "U1", "38"), ("C26", "VIN_IC", "U1", "30"),
                                  ("C27", "EXTVCC", "U1", "32"), ("C28", "+5V_CC", "U2", "5"), ("C29", "+5V_CC", "U3", "5"),
                                  ("C31", "VREF_CC", "U3", "3"), ("C33", "+5V_CC", "U4", "1")):
        add(f"{cap} to {ic} pin {pin} {netname} (edge)", edge(cap, dict(netname=netname), ic, dict(pins=[pin])), 4)
    add("C23 (10 uF) to U1 DRVCC pin 26 (edge)", edge("C23", dict(netname="DRVCC"), "U1", dict(pins=["26"])), 30)

    # courtyards: no overlap, nothing inside the board edge keep-out, nothing under L1
    cy = {}
    for ref, f in fps.items():
        f.BuildCourtyardCaches()
        poly = f.GetCourtyard(pcbnew.F_CrtYd)
        if poly.OutlineCount():
            cy[ref] = poly
    overlaps = []
    refs = sorted(cy)
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            if not cy[a].BBox().Intersects(cy[b].BBox()):
                continue
            inter = pcbnew.SHAPE_POLY_SET(cy[a])
            inter.BooleanIntersection(cy[b], pcbnew.SHAPE_POLY_SET.PM_FAST)
            if inter.Area() > 0:
                overlaps.append(f"{a}/{b} ({inter.Area() / 1e12:.2f} mm2)")
    outside = []
    for ref, f in fps.items():
        for p in f.Pads():
            r = rect(p)
            if min(r[0], r[1]) < 0.5 or r[2] > W - 0.5 or r[3] > H - 0.5:
                outside.append(ref)
                break
    # pad to pad between different parts and different nets
    allpads = [(ref, p, rect(p)) for ref, f in fps.items() for p in f.Pads() if p.GetNumber()]
    close = []
    for i, (ra, pa, a) in enumerate(allpads):
        for rb, pb, b in allpads[i + 1:]:
            if ra == rb:
                continue
            if not (pa.IsOnLayer(pcbnew.F_Cu) and pb.IsOnLayer(pcbnew.F_Cu)):
                continue
            g = gap(a, b)
            if g < 0.5:
                close.append((round(g, 2), f"{ra}.{pa.GetNumber()}/{rb}.{pb.GetNumber()}"))
    holes = []
    for h in ("H1", "H2", "H3", "H4"):
        hx, hy, _ = PLACE[h]
        edge_d = min(hx, hy, W - hx, H - hy)
        near = min((math.hypot(max(r[0] - hx, hx - r[2], 0), max(r[1] - hy, hy - r[3], 0)), ref)
                   for ref, p, r in allpads if not ref.startswith("H"))
        holes.append((h, edge_d, near))
    vin_area = sum(z.GetFilledArea() for z in board.Zones() if z.GetNetname() == "VIN" and z.GetLayer() == pcbnew.F_Cu) / 1e12
    areas = {}
    for z in board.Zones():
        key = f"{z.GetNetname()} {board.GetLayerName(z.GetLayer())}"
        areas[key] = areas.get(key, 0) + z.GetFilledArea() / 1e12
    return rows, overlaps, outside, sorted(close), holes, vin_area, areas


def mark_dnp():
    """KiCad 7 has no "do not populate" flag on footprints, KiCad 8+ has one and compares it with the schematic.
    The board is first saved as KiCad 7 writes it (copy in out/, used by kicad-cli 7 and pcbnew 7); then the flag is
    added to the footprints of the unpopulated parts in the board file itself."""
    with open(PCB, encoding="utf-8") as f:
        txt = f.read()
    with open(K7_COPY, "w", encoding="utf-8") as f:
        f.write(txt)
    done = set()
    for m in list(re.finditer(r'\(footprint "[^"]+"', txt))[::-1]:
        end = txt.find('(footprint "', m.end())
        block = txt[m.start():end if end > 0 else len(txt)]
        ref = re.search(r'\(fp_text reference "([^"]+)"', block)
        if ref and ref.group(1) in DNP_REFS:
            new_block, n = re.subn(r"\(attr ([a-z_ ]+)\)", lambda a: f"(attr {a.group(1)} dnp)", block, count=1)
            if n:
                txt = txt[:m.start()] + new_block + txt[m.start() + len(block):]
                done.add(ref.group(1))
    if done != DNP_REFS:
        raise SystemExit(f"DNP flag not written for {sorted(DNP_REFS - done)}")
    with open(PCB, "w", encoding="utf-8") as f:
        f.write(txt)


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    stamp = os.path.join(HERE, "out", "pcb_generated.sha256")
    if os.path.exists(PCB) and "--force" not in sys.argv:
        known = open(stamp).read().split()[0] if os.path.exists(stamp) else ""
        if sha(PCB) != known:
            raise SystemExit(f"{os.path.basename(PCB)} was changed after this script wrote it (or was not written by it).\n"
                             "Nothing was overwritten. Use --force only if those changes may be lost.")
    board, comps, nodes = build()
    pcbnew.SaveBoard(PCB, board, True)                    # True: leave the hand-written .kicad_pro alone
    board = pcbnew.LoadBoard(PCB)                         # reload with the project (net classes)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    for z in board.Zones():
        z.CalculateFilledArea()
    pcbnew.SaveBoard(PCB, board, True)
    mark_dnp()
    with open(stamp, "w") as f:
        f.write(sha(PCB) + "  " + os.path.basename(PCB) + "\n")
    rows, overlaps, outside, close, holes, vin_area, areas = checks(board, nodes)
    lines = ["| Check | Value (mm) | Limit | Result |", "|---|---|---|---|"]
    lines += [f"| {w} | {v:.2f} | {lim} | {res} |" for w, v, lim, res in rows]
    report = "\n".join(lines)
    report += f"\n\nFootprints: {len(board.GetFootprints())}, nets: {board.GetNetCount() - 1}, pads with a net: " \
              f"{sum(1 for f in board.GetFootprints() for p in f.Pads() if p.GetNetname())}"
    report += f"\nCourtyard overlaps: {overlaps or 'none'}"
    report += f"\nPads closer than 0.5 mm to the board edge: {outside or 'none'}"
    report += f"\nPads of different parts closer than 0.5 mm (same net included): {close or 'none'}"
    for h, e, (d, ref) in holes:
        report += f"\n{h}: {e:.1f} mm from the edge; nearest pad {ref} at {d:.1f} mm from the hole centre"
    report += f"\nVIN copper on the top layer (Q1 drain pour): {vin_area:.0f} mm2 = {vin_area / 100:.1f} cm2 (target 10 cm2)"
    report += "\nFilled copper per zone (mm2): " + ", ".join(f"{k}: {v:.0f}" for k, v in sorted(areas.items()))
    print(report)
    with open(os.path.join(HERE, "out", "placement_checks.md"), "w", encoding="utf-8") as f:
        f.write("# Placement checks (make_pcb.py)\n\n" + report + "\n")


if __name__ == "__main__":
    main()
