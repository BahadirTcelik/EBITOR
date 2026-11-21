"""Generate the KiCad project from kicad/netlist/schematic_netlist.py (the single source of the design).

Outputs, all next to this file:
  ee463_dcdc.kicad_sch   schematic (file format of KiCad 7; KiCad 8, 9 and 10 open and convert it)
  ee463_dcdc.kicad_pro   project file with the net classes of layout_plan.md
  ee463.kicad_sym        project symbol library (LTC3895, drawn from the Rev A pin configuration)
  ee463.pretty/          project footprint library (LTC3895 FE38(31) with exposed pad and thermal vias;
                         generic 5.00 mm terminal block)
  sym-lib-table, fp-lib-table
  footprints_used.txt    list read by run_kicad_checks.bat

The schematic is a connection schematic: parts are grouped by block and every pin carries a net label
(GND pins carry a GND symbol). It is complete electrically; redraw the wiring by hand only if a prettier
drawing is wanted. Regenerating OVERWRITES ee463_dcdc.kicad_sch.

Needs: Python 3, `pip install sexpdata`, and the KiCad symbol libraries (set KICAD_SYMBOL_DIR;
on Windows e.g. "C:\\Program Files\\KiCad\\10.0\\share\\kicad\\symbols"). Standard symbols are copied
from those libraries into the schematic, so the result does not depend on the library version afterwards.
"""
import copy
import json
import os
import sys
import uuid

import sexpdata
from sexpdata import Symbol as S

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "netlist"))
import schematic_netlist as NL  # noqa: E402  (also regenerates pins.csv, nets.csv and the BOM)

SYMDIR = os.environ.get("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")
PROJECT = "ee463_dcdc"
DATE = "2026-11-16"
REV = "A"
NS = uuid.UUID("5b1f0d4e-463a-4c5d-9e63-0000ee463000")
U1_FP = "LTC3895_TSSOP-38-31-1EP_4.4x9.7mm_P0.5mm_EP2.74x4.75mm_ThermalVias"


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


ROOT = uid("root-sheet")


# ----------------------------------------------------------------------------- s-expression helpers
def tag(e):
    return e[0].value() if isinstance(e, list) and e and isinstance(e[0], S) else None


def atom(a):
    if isinstance(a, S):
        return a.value()
    if isinstance(a, str):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(a, float):
        s = f"{a:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(a)


def flat(e):
    return "(" + " ".join(flat(x) if isinstance(x, list) else atom(x) for x in e) + ")"


def dump(e, ind=0):
    pad = "  " * ind
    one = flat(e)
    if len(one) + len(pad) <= 118 or not any(isinstance(x, list) for x in e):
        return pad + one
    head = []
    i = 0
    while i < len(e) and not isinstance(e[i], list):
        head.append(atom(e[i]))
        i += 1
    lines = [pad + "(" + " ".join(head)]
    for x in e[i:]:
        lines.append(dump(x, ind + 1) if isinstance(x, list) else "  " * (ind + 1) + atom(x))
    lines.append(pad + ")")
    return "\n".join(lines)


def L(name, *items):
    return [S(name), *items]


def font(size=1.27, bold=False):
    f = L("font", L("size", size, size))
    if bold:
        f.append(S("bold"))
    return f


def effects(justify=None, hide=False, size=1.27, bold=False):
    e = L("effects", font(size, bold))
    if justify:
        e.append(L("justify", *[S(j) for j in justify.split()]))
    if hide:
        e.append(S("hide"))
    return e


STROKE = L("stroke", L("width", 0), L("type", S("default")))


# ----------------------------------------------------------------------------- symbol libraries
_libs = {}


def lib(name):
    if name not in _libs:
        with open(os.path.join(SYMDIR, name + ".kicad_sym"), encoding="utf-8") as f:
            _libs[name] = sexpdata.loads(f.read(), nil=None, true=None)
    return _libs[name]


def raw_symbol(libname, name):
    for e in lib(libname)[1:]:
        if tag(e) == "symbol" and e[1] == name:
            return e
    raise KeyError(f"{libname}:{name} not found in {SYMDIR}")


def flat_symbol(libname, name):
    """Library symbol with 'extends' resolved, as KiCad stores it inside a schematic."""
    s = raw_symbol(libname, name)
    ext = [e for e in s if tag(e) == "extends"]
    if not ext:
        return copy.deepcopy(s)
    parent = flat_symbol(libname, ext[0][1])
    pname = parent[1]
    props = {e[1]: e for e in s if tag(e) == "property"}
    out = [parent[0], name]
    for e in parent[2:]:
        if tag(e) == "symbol":
            e = copy.deepcopy(e)
            e[1] = name + e[1][len(pname):]
        elif tag(e) == "property" and e[1] in props:
            e = copy.deepcopy(props.pop(e[1]))
        out.append(e)
    first_unit = next(i for i, e in enumerate(out) if tag(e) == "symbol")
    out[first_unit:first_unit] = [copy.deepcopy(p) for p in props.values()]
    return out


def sym_pins(symdef):
    pins = []
    for unit in symdef:
        if tag(unit) != "symbol":
            continue
        for p in unit:
            if tag(p) == "pin":
                d = {tag(k): k for k in p if isinstance(k, list)}
                at = d["at"]
                pins.append(dict(number=d["number"][1], name=d["name"][1], x=at[1], y=at[2],
                                 a=int(at[3]) if len(at) > 3 else 0, etype=p[1].value()))
    return pins


def sym_props(symdef):
    return {e[1]: e for e in symdef if tag(e) == "property"}


# ----------------------------------------------------------------------------- LTC3895 symbol (project library)
U1_PINS = {  # number: (name, electrical type) - Rev A (3895fa) pin configuration, page 2
    1: ("OVLO", "input"), 2: ("VPRG", "input"), 3: ("SENSE+", "input"), 4: ("SENSE-", "input"), 5: ("SS", "passive"),
    6: ("VFB", "input"), 7: ("ITH", "passive"), 8: ("MODE", "input"), 9: ("GND", "power_in"), 10: ("CPUMP_EN", "input"),
    11: ("CLKOUT", "output"), 12: ("GND", "power_in"), 13: ("PLLIN", "input"), 14: ("PGOOD", "open_collector"),
    15: ("GND", "power_in"), 16: ("NC", "no_connect"), 17: ("FREQ", "passive"), 18: ("DRVSET", "input"),
    19: ("DRVUV", "input"), 20: ("TG", "output"), 21: ("SW", "passive"), 22: ("BOOST", "passive"), 24: ("BG", "output"),
    26: ("DRVCC", "power_out"), 28: ("NDRV", "passive"), 30: ("VIN", "power_in"), 32: ("EXTVCC", "power_in"),
    34: ("RUN", "input"), 36: ("PHASMD", "input"), 37: ("ILIM", "input"), 38: ("INTVCC", "power_out"),
    39: ("GND", "power_in"),
}


def ltc3895_symbol():
    name = "LTC3895xFE"

    def pin(num, x, y, a):
        nm, et = U1_PINS[num]
        return L("pin", S(et), S("line"), L("at", x, y, a), L("length", 2.54),
                 L("name", nm, effects()), L("number", str(num), effects()))

    pins = [pin(n, -15.24, 22.86 - 2.54 * (n - 1), 0) for n in range(1, 20)]
    pins += [pin(n, 15.24, 22.86 - 2.54 * (38 - n), 180) for n in range(20, 39) if n in U1_PINS]
    pins.append(pin(39, 0, -27.94, 90))
    return L("symbol", name, L("in_bom", S("yes")), L("on_board", S("yes")),
             L("property", "Reference", "U", L("at", -12.7, 26.67, 0), effects("left")),
             L("property", "Value", name, L("at", 1.27, 26.67, 0), effects("left")),
             L("property", "Footprint", "ee463:" + U1_FP, L("at", 0, -35.56, 0), effects(hide=True)),
             L("property", "Datasheet", "https://www.analog.com/LTC3895", L("at", 0, -38.1, 0), effects(hide=True)),
             L("property", "ki_keywords", "synchronous buck controller 150V", L("at", 0, 0, 0), effects(hide=True)),
             L("property", "ki_description",
               "150 V low IQ synchronous step-down controller, TSSOP-38 with 31 leads (FE38(31)) and exposed pad",
               L("at", 0, 0, 0), effects(hide=True)),
             L("symbol", name + "_0_1",
               L("rectangle", L("start", -12.7, 25.4), L("end", 12.7, -25.4),
                 L("stroke", L("width", 0.254), L("type", S("default"))), L("fill", L("type", S("background"))))),
             L("symbol", name + "_1_1", *pins))


# ----------------------------------------------------------------------------- LTC3895 footprint
def ltc3895_footprint():
    """FE38(31): LTC drawing 05-08-1865 Rev B (datasheet Rev A, page 36).
    Recommended layout: pads 0.315 +-0.05 x 1.05 +-0.10 at 0.50 pitch, 6.60 over the pad rows (4.50 inside),
    exposed pad 2.74 x 4.75. Leads 23, 25, 27, 29, 31, 33, 35 are removed."""
    pw, pl, span = 0.30, 1.05, 6.60
    xc = (span - pl) / 2
    ep_w, ep_h = 2.74, 4.75
    lay_smd = L("layers", "F.Cu", "F.Paste", "F.Mask")
    items = []

    def line(x1, y1, x2, y2, layer, w):
        items.append(L("fp_line", L("start", x1, y1), L("end", x2, y2), L("stroke", L("width", w), L("type", S("solid"))),
                       L("layer", layer)))

    def text(kind, txt, y, layer, hide=False):
        t = L("fp_text", S(kind), txt, L("at", 0, y), L("layer", layer))
        if hide:
            t.append(S("hide"))
        t.append(L("effects", L("font", L("size", 1, 1), L("thickness", 0.15))))
        items.append(t)

    text("reference", "REF**", -6.2, "F.SilkS")
    text("value", U1_FP, 6.2, "F.Fab")
    text("user", "${REFERENCE}", 0, "F.Fab")
    for sx in (-1, 1):                                    # silkscreen along the two short edges
        line(-2.2, sx * 4.96, 2.2, sx * 4.96, "F.SilkS", 0.12)
    line(-3.3, -4.96, -2.2, -4.96, "F.SilkS", 0.12)       # pin 1 mark: longer line at pin 1
    body = [(-1.2, -4.85), (2.2, -4.85), (2.2, 4.85), (-2.2, 4.85), (-2.2, -3.85), (-1.2, -4.85)]
    for (x1, y1), (x2, y2) in zip(body, body[1:]):
        line(x1, y1, x2, y2, "F.Fab", 0.1)
    cx, cy = 3.55, 5.1
    for (x1, y1), (x2, y2) in zip([(-cx, -cy), (cx, -cy), (cx, cy), (-cx, cy)], [(cx, -cy), (cx, cy), (-cx, cy), (-cx, -cy)]):
        line(x1, y1, x2, y2, "F.CrtYd", 0.05)
    for n in range(1, 39):
        if n not in U1_PINS:
            continue
        x = -xc if n <= 19 else xc
        y = -4.5 + 0.5 * (n - 1) if n <= 19 else 4.5 - 0.5 * (n - 20)
        items.append(L("pad", str(n), S("smd"), S("roundrect"), L("at", x, y), L("size", pl, pw), lay_smd,
                       L("roundrect_rratio", 0.25)))
    items.append(L("pad", "39", S("smd"), S("rect"), L("at", 0, 0), L("size", ep_w, ep_h), L("layers", "F.Cu", "F.Mask")))
    items.append(L("pad", "39", S("smd"), S("rect"), L("at", 0, 0), L("size", ep_w, ep_h), L("layers", "B.Cu", "B.Mask")))
    for x in (-0.8, 0, 0.8):                              # 3 x 3 thermal vias, 0.3 mm drill, 0.6 mm pad
        for y in (-1.6, 0, 1.6):
            items.append(L("pad", "39", S("thru_hole"), S("circle"), L("at", x, y), L("size", 0.6, 0.6), L("drill", 0.3),
                           L("layers", "*.Cu")))
    for y, h in ((-2.125, 0.35), (-0.8, 0.9), (0.8, 0.9), (2.125, 0.35)):   # paste between the via rows
        items.append(L("pad", "", S("smd"), S("rect"), L("at", 0, y), L("size", 2.3, h), L("layers", "F.Paste")))
    return L("footprint", U1_FP, L("version", 20221018), L("generator", "ee463_make_kicad"), L("layer", "F.Cu"),
             L("descr", "LTC3895 FE38(31): TSSOP-38 4.4 x 9.7 mm, 0.5 mm pitch, leads 23/25/27/29/31/33/35 removed, exposed pad "
                        "2.74 x 4.75 mm with 3 x 3 thermal vias (LTC DWG 05-08-1865 Rev B, datasheet Rev A page 36)"),
             L("tags", "TSSOP FE38 LTC3895 exposed pad"), L("attr", S("smd")), *items)


TB_FP = "TerminalBlock_Generic_1x02_P5.00mm_Drill1.5mm"


def terminal_footprint():
    """Generic 2-position screw terminal block, 5.00 mm pitch. The part is chosen by price, so the footprint is tolerant:
    1.5 mm holes take flat pins up to about 1.0 x 1.0 mm and also a 5.08 mm part (0.04 mm per pin).
    Pad 1 is at the origin (square), pad 2 at +5.00 mm. Outline 10 x 8 mm is a typical body; wire entry on the -y side."""
    items = []

    def line(x1, y1, x2, y2, layer, w):
        items.append(L("fp_line", L("start", x1, y1), L("end", x2, y2), L("stroke", L("width", w), L("type", S("solid"))),
                       L("layer", layer)))

    def box(x1, y1, x2, y2, layer, w):
        for a, b in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))):
            line(*a, *b, layer, w)

    def text(kind, txt, x, y, layer):
        items.append(L("fp_text", S(kind), txt, L("at", x, y), L("layer", layer),
                       L("effects", L("font", L("size", 1, 1), L("thickness", 0.15)))))

    text("reference", "REF**", 2.5, -5.6, "F.SilkS")
    text("value", TB_FP, 2.5, 5.6, "F.Fab")
    text("user", "${REFERENCE}", 2.5, 2.6, "F.Fab")
    box(-2.5, -4.0, 7.5, 4.0, "F.Fab", 0.1)
    box(-2.62, -4.12, 7.62, 4.12, "F.SilkS", 0.12)
    line(-2.62, -3.2, 7.62, -3.2, "F.SilkS", 0.12)          # wire-entry side
    line(-3.1, -4.12, -3.1, -2.6, "F.SilkS", 0.12)          # pin 1 mark
    box(-3.0, -4.5, 8.0, 4.5, "F.CrtYd", 0.05)
    items.append(L("pad", "1", S("thru_hole"), S("rect"), L("at", 0, 0), L("size", 2.8, 2.8), L("drill", 1.5),
                   L("layers", "*.Cu", "*.Mask")))
    items.append(L("pad", "2", S("thru_hole"), S("circle"), L("at", 5, 0), L("size", 2.8, 2.8), L("drill", 1.5),
                   L("layers", "*.Cu", "*.Mask")))
    return L("footprint", TB_FP, L("version", 20221018), L("generator", "ee463_make_kicad"), L("layer", "F.Cu"),
             L("descr", "Generic screw terminal block, 2 positions, 5.00 mm pitch, 1.5 mm holes, 2.8 mm pads "
                        "(body outline 10 x 8 mm is typical: check the part that is bought)"),
             L("tags", "screw terminal block 5.00mm"), L("attr", S("through_hole")), *items)


# ----------------------------------------------------------------------------- component -> symbol
def symbol_for(c):
    ref = c["ref"]
    if ref == "U1":
        return "ee463", "LTC3895xFE"
    table = {"U2": ("Amplifier_Current", "INA180A2"), "U3": ("Amplifier_Operational", "MCP6001-OT"),
             "U4": ("Reference_Voltage", "TL431DBZ"), "U5": ("Regulator_Linear", "HT75xx-1-SOT89"), "D3": ("Device", "D_Zener")}
    if ref in table:
        return table[ref]
    if ref.startswith("RV"):
        return "Device", "R_Potentiometer"
    if ref.startswith("TP"):
        return "Connector", "TestPoint"
    for prefix, name in (("R", ("Device", "R")), ("L", ("Device", "L")), ("D", ("Device", "D")),
                         ("J", ("Connector", "Screw_Terminal_01x02")), ("H", ("Mechanical", "MountingHole"))):
        if ref.startswith(prefix):
            return name
    if ref.startswith("C"):
        return ("Device", "C_Polarized") if "+" in c["pins"] else ("Device", "C")
    if ref.startswith("Q"):
        return "Transistor_FET", c["value"]
    raise KeyError(ref)


SYMS = {}   # (lib, name) -> flattened definition


def symdef(libname, name):
    key = (libname, name)
    if key not in SYMS:
        SYMS[key] = ltc3895_symbol() if libname == "ee463" else flat_symbol(libname, name)
    return SYMS[key]


# ----------------------------------------------------------------------------- schematic model
def tf(rot, x, y):
    """Library coordinates (y up) -> schematic offset (y down) for a symbol rotated by rot degrees."""
    return {0: (x, -y), 90: (-y, -x), 180: (-x, y), 270: (y, x)}[rot]


OUT = {0: (-1, 0), 90: (0, -1), 180: (1, 0), 270: (0, 1)}        # outward direction of a pin, library coordinates
LABEL = {(1, 0): (0, "left"), (-1, 0): (180, "right"), (0, -1): (90, "left"), (0, 1): (270, "right")}
GNDROT = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}
STUB = 2.54

sch_wires, sch_nc, sch_labels, sch_symbols, sch_text, sch_rect = [], [], [], [], [], []
counters = {"pwr": 0, "flg": 0}
placed_nodes = []       # (ref, pin number, net) of everything drawn, for the self-check


def r4(v):
    return round(v + 0.0, 4)


def instance(ref, libid, x, y, rot, props, pin_numbers, dnp=False, in_bom=True, on_board=True):
    e = L("symbol", L("lib_id", libid), L("at", r4(x), r4(y), rot), L("unit", 1),
          L("in_bom", S("yes" if in_bom else "no")), L("on_board", S("yes" if on_board else "no")),
          L("dnp", S("yes" if dnp else "no")), L("uuid", S(uid("sym", ref))))
    e += props
    for n in pin_numbers:
        e.append(L("pin", n, L("uuid", S(uid("pin", ref, n)))))
    e.append(L("instances", L("project", PROJECT, L("path", "/" + ROOT, L("reference", ref), L("unit", 1)))))
    sch_symbols.append(e)


def prop(name, value, x, y, angle=0, justify=None, hide=False):
    return L("property", name, value, L("at", r4(x), r4(y), angle), effects(justify, hide))


def attach(net, x, y, d, owner):
    """Connect net to the point (x, y); d is the outward direction on the sheet."""
    if net == "NC":
        sch_nc.append(L("no_connect", L("at", r4(x), r4(y)), L("uuid", S(uid("nc", owner)))))
        return
    x2, y2 = x + STUB * d[0], y + STUB * d[1]
    sch_wires.append(L("wire", L("pts", L("xy", r4(x), r4(y)), L("xy", r4(x2), r4(y2))), STROKE,
                       L("uuid", S(uid("wire", owner)))))
    if net == "GND":
        counters["pwr"] += 1
        ref = f"#PWR{counters['pwr']:03d}"
        rot = GNDROT[d]
        vx, vy = tf(rot, 0, -3.81)
        instance(ref, "power:GND", x2, y2, rot,
                 [prop("Reference", ref, x2, y2 + 6.35, hide=True),
                  prop("Value", "GND", x2 + vx, y2 + vy, hide=(rot != 0)),
                  prop("Footprint", "", x2, y2, hide=True), prop("Datasheet", "", x2, y2, hide=True)], ["1"])
        return
    ang, just = LABEL[d]
    sch_labels.append(L("global_label", net, L("shape", S("passive")), L("at", r4(x2), r4(y2), ang), effects(just),
                        L("uuid", S(uid("label", owner))),
                        L("property", "Intersheetrefs", "${INTERSHEET_REFS}", L("at", 0, 0, 0), effects(hide=True))))


def place(c, x, y, rot=0, row=False):
    libname, name = symbol_for(c)
    sd = symdef(libname, name)
    pins = sym_pins(sd)
    ref = c["ref"]
    netof = {}
    for key, net in c["pins"].items():
        for num in NL.pads(c, key):
            netof[num] = net
    missing = set(netof) - {p["number"] for p in pins}
    extra = {p["number"] for p in pins} - set(netof)
    if missing or extra:
        raise SystemExit(f"{ref}: symbol {libname}:{name} pins do not match the netlist (missing {missing}, extra {extra})")
    lp = sym_props(sd)
    fp = c["fp"]
    props = []
    if row:        # two-pin part or test point drawn horizontally: reference and value on one line above it
        fa = 90 if rot in (90, 270) else 0      # field angle that reads horizontally on a rotated symbol
        dx = -3.81 if ref.startswith("TP") else 0
        jr, jl = ("left", "right") if fa else ("right", "left")     # justification is mirrored on a rotated symbol
        props += [prop("Reference", ref, x + dx - 0.635, y - 2.794, fa, jr),
                  prop("Value", c["value"], x + dx + 0.635, y - 2.794, fa, jl)]
    else:
        for pname, val in (("Reference", ref), ("Value", c["value"])):
            at = lp[pname][3]
            ox, oy = tf(rot, at[1], at[2])
            eff = copy.deepcopy(next(k for k in lp[pname] if tag(k) == "effects"))
            props.append(L("property", pname, val, L("at", r4(x + ox), r4(y + oy), int(at[3]) if len(at) > 3 else 0), eff))
    props += [prop("Footprint", fp, x, y, hide=True),
              prop("Datasheet", lp["Datasheet"][2] if "Datasheet" in lp else "", x, y, hide=True),
              prop("MPN", c["mpn"], x, y, hide=True)]
    instance(ref, f"{libname}:{name}", x, y, rot, props, [p["number"] for p in pins], dnp=not c["fit"],
             on_board=True, in_bom=True)
    done = set()
    for p in pins:
        px, py = tf(rot, p["x"], p["y"])
        gx, gy = r4(x + px), r4(y + py)
        placed_nodes.append((ref, p["number"], netof[p["number"]]))
        if (gx, gy) in done:        # stacked pins (MOSFET source pads 1-3) share one connection
            continue
        done.add((gx, gy))
        attach(netof[p["number"]], gx, gy, tf(rot, *OUT[p["a"]]), f"{ref}.{p['number']}")


def flag(net, x, y):
    counters["flg"] += 1
    ref = f"#FLG{counters['flg']:02d}"
    instance(ref, "power:PWR_FLAG", x, y, 0,
             [prop("Reference", ref, x, y - 5.08, hide=True), prop("Value", "PWR_FLAG", x, y - 3.81),
              prop("Footprint", "", x, y, hide=True), prop("Datasheet", "", x, y, hide=True)], ["1"])
    symdef("power", "PWR_FLAG")
    attach(net, x, y, (0, 1), ref)


# ----------------------------------------------------------------------------- layout (A3 sheet, 1.27 mm grid)
COL, ROW = 43.18, 7.62
BIG = {  # cell width, cell height, symbol origin inside the cell
    "U1": (71.12, 71.12, 35.56, 33.02), "J": (40.64, 20.32, 25.4, 10.16), "Q": (45.72, 45.72, 22.86, 22.86),
    "U2": (50.8, 45.72, 25.4, 25.4), "U3": (50.8, 45.72, 25.4, 25.4), "U4": (40.64, 35.56, 17.78, 22.86),
    "U5": (48.26, 27.94, 22.86, 12.7), "RV": (40.64, 45.72, 17.78, 22.86)}
TITLE_H = 7.62


def cell_of(ref):
    for k in ("U1", "U2", "U3", "U4", "U5", "RV", "J", "Q"):
        if ref.startswith(k):
            return BIG[k]
    return None


def frame(title, x0, y0, x1, y1):
    sch_rect.append(L("rectangle", L("start", r4(x0), r4(y0)), L("end", r4(x1), r4(y1)),
                      L("stroke", L("width", 0), L("type", S("dash"))), L("fill", L("type", S("none"))),
                      L("uuid", S(uid("rect", title)))))
    sch_text.append(L("text", title, L("at", r4(x0 + 2.54), r4(y0 + 5.08), 0), effects("left bottom", size=2.0, bold=True),
                      L("uuid", S(uid("title", title)))))


def block(title, x0, y0, comps, rows_per_col, rows_right=False):
    """Big parts in a strip at the top; two-pin parts in columns below it (or to the right of it)."""
    bigs = [c for c in comps if cell_of(c["ref"])]
    rows = [c for c in comps if not cell_of(c["ref"])]
    x, y = x0, y0 + TITLE_H
    strip_h = 0
    for c in bigs:
        w, h, ox, oy = cell_of(c["ref"])
        place(c, x + ox, y + oy, 0)
        x += w
        strip_h = max(strip_h, h)
    rx0, ry0 = (x, y + 5.08) if rows_right else (x0, y + strip_h + (5.08 if bigs else 3.81))
    xmax, ymax = x, y + strip_h
    for i, c in enumerate(rows):
        cx = round((rx0 + (i // rows_per_col) * COL + COL / 2) / 1.27) * 1.27
        cy = ry0 + (i % rows_per_col) * ROW
        ref = c["ref"]
        if ref.startswith("TP"):
            place(c, cx - 5.08, cy, 90, row=True)
        else:
            place(c, cx, cy, 0 if ref.startswith("D") else 90, row=True)
        xmax = max(xmax, rx0 + (i // rows_per_col + 1) * COL)
        ymax = max(ymax, cy + ROW / 2)
    frame(title, x0, y0, xmax, ymax + 1.27)
    return r4(xmax), r4(ymax + 1.27)


def build():
    blocks = []
    for c in NL.C:
        if c["block"] not in blocks:
            blocks.append(c["block"])
    by = {b: [c for c in NL.C if c["block"] == b] for b in blocks}
    b_in, b_pwr, b_ctl, b_cc, b_tp = blocks
    gap, top = 3.81, 12.7
    x1, y1 = block(b_in, 12.7, top, by[b_in], 7)
    x2, y2 = block(b_pwr, x1 + gap, top, by[b_pwr], 6)
    x3, y3 = block(b_ctl, x2 + gap, top, by[b_ctl], 11, rows_right=True)
    y_mid = max(y1, y2, y3) + gap
    x4, y4 = block(b_cc, 12.7, y_mid, by[b_cc], 3)
    x5, y5 = block("5 Test points", x4 + gap, y_mid, [c for c in by[b_tp] if c["ref"].startswith("TP")], 11)
    # mounting holes
    y_low = y4 + gap
    holes = [c for c in by[b_tp] if c["ref"].startswith("H")]
    for i, c in enumerate(holes):
        hx, hy = 12.7 + 12.7 + i * 20.32, y_low + 17.78
        libname, name = symbol_for(c)
        lp = sym_props(symdef(libname, name))
        instance(c["ref"], f"{libname}:{name}", hx, hy, 0,
                 [prop("Reference", c["ref"], hx, hy - 3.81), prop("Value", c["value"], hx, hy + 3.81),
                  prop("Footprint", c["fp"], hx, hy, hide=True), prop("Datasheet", lp["Datasheet"][2], hx, hy, hide=True),
                  prop("MPN", c["mpn"], hx, hy, hide=True)], [], in_bom=False)
    xh = 12.7 + 20.32 * len(holes) + 5.08
    frame("Mounting holes", 12.7, y_low, xh, y_low + 25.4)
    # power flags: nets that feed a power-input pin through passive parts only (needed by the ERC, not by the board)
    nets = ["GND", "VIN_IC", "EXTVCC", "LDO_IN" if "LDO_IN" in NL.nets else "+5V_CC"]   # +5V_CC: fed through R29, regulated by the TL431
    fx = xh + gap
    for i, net in enumerate(nets):
        flag(net, round((fx + 10.16 + i * 15.24) / 1.27) * 1.27, round((y_low + 15.24) / 1.27) * 1.27)
    xf = fx + 15.24 * len(nets) + 5.08
    frame("Power flags (ERC only)", fx, y_low, xf, y_low + 38.1)
    note = (f"Generated by kicad/make_kicad.py from kicad/netlist/schematic_netlist.py ({len(NL.C)} parts).\n"
            "Connections are made by net labels; GND pins carry a GND symbol.\n"
            "Parts marked with a cross are not populated (DNP): footprint only.\n"
            "Net names VIN, VOUT, GND and SW are required by PCB-Checker - do not rename.\n"
            "Pin numbers checked against the datasheets on 16 Nov 2026: kicad/footprints.md.\n"
            "Assembly groups A / B / C: see the BOM (bom/ee463_bom.csv) and kicad/layout_plan.md.")
    sch_text.append(L("text", note, L("at", r4(xf + gap + 1.27), r4(y_low + 2.54), 0), effects("left top", size=1.5),
                      L("uuid", S(uid("note")))))


def self_check():
    """Everything drawn must equal pins.csv (the same data, but this catches a symbol with a wrong pin set)."""
    want = set()
    for c in NL.C:
        for key, net in c["pins"].items():
            for num in NL.pads(c, key):
                want.add((c["ref"], num, net))
    got = set(placed_nodes)
    if want != got:
        raise SystemExit(f"self-check failed: missing {sorted(want - got)[:10]}, extra {sorted(got - want)[:10]}")


# ----------------------------------------------------------------------------- writers
def write_schematic():
    symdef("power", "GND")
    libsyms = []
    for (libname, name) in sorted(SYMS):
        d = copy.deepcopy(SYMS[(libname, name)])
        d[1] = f"{libname}:{name}"
        libsyms.append(d)
    sch = L("kicad_sch", L("version", 20230121), L("generator", S("eeschema")), L("uuid", S(ROOT)), L("paper", "A3"),
            L("title_block", L("title", "EE463 60 W synchronous buck converter, 20-48 V to 12 V / 5 A"),
              L("date", DATE), L("rev", REV), L("company", "METU EEE - EE463 hardware project"),
              L("comment", 1, "Generated from kicad/netlist/schematic_netlist.py by kicad/make_kicad.py")),
            L("lib_symbols", *libsyms),
            *sch_nc, *sch_wires, *sch_rect, *sch_text, *sch_labels, *sch_symbols,
            L("sheet_instances", L("path", "/", L("page", "1"))))
    with open(os.path.join(HERE, PROJECT + ".kicad_sch"), "w", encoding="utf-8", newline="\n") as f:
        f.write(dump(sch) + "\n")


def write_libs():
    with open(os.path.join(HERE, "ee463.kicad_sym"), "w", encoding="utf-8", newline="\n") as f:
        f.write(dump(L("kicad_symbol_lib", L("version", 20220914), L("generator", S("ee463_make_kicad")), ltc3895_symbol())) + "\n")
    os.makedirs(os.path.join(HERE, "ee463.pretty"), exist_ok=True)
    with open(os.path.join(HERE, "ee463.pretty", U1_FP + ".kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
        f.write(dump(ltc3895_footprint()) + "\n")
    with open(os.path.join(HERE, "ee463.pretty", TB_FP + ".kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
        f.write(dump(terminal_footprint()) + "\n")
    with open(os.path.join(HERE, "sym-lib-table"), "w", newline="\n") as f:
        f.write('(sym_lib_table\n  (lib (name "ee463")(type "KiCad")(uri "${KIPRJMOD}/ee463.kicad_sym")(options "")'
                '(descr "EE463 project symbols"))\n)\n')
    with open(os.path.join(HERE, "fp-lib-table"), "w", newline="\n") as f:
        f.write('(fp_lib_table\n  (lib (name "ee463")(type "KiCad")(uri "${KIPRJMOD}/ee463.pretty")(options "")'
                '(descr "EE463 project footprints"))\n)\n')
    with open(os.path.join(HERE, "footprints_used.txt"), "w", newline="\r\n") as f:
        for fp in sorted({c["fp"] for c in NL.C}):
            f.write(fp + "\n")


def write_project():
    def cls(name, width, clearance):
        return {"bus_width": 12, "clearance": clearance, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
                "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1, "name": name,
                "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": width,
                "via_diameter": 0.6, "via_drill": 0.3, "wire_width": 6}
    classes = {  # kicad/layout_plan.md section 4
        "PWR_IN": (1.7, 0.5, ["VIN", "VIN_RTN", "CBULK_N"]),
        "PWR_OUT": (3.2, 0.2, ["SW", "SNS_P", "VOUT_C", "VOUT"]),   # SW: 0.5 mm clearance by the rule in .kicad_dru
        "GND": (0.5, 0.2, ["GND"]),
        "GATE": (0.5, 0.2, ["TG", "TG_G", "BG", "BG_G", "BOOST"]),
        "AUX": (0.4, 0.2, [n for n in ("DRVCC", "EXTVCC", "VIN_IC", "LDO_IN", "+5V_CC", "INTVCC") if n in NL.nets]),
    }
    known = {n for comp in NL.C for n in comp["pins"].values()}
    for name, (_, _, nets) in classes.items():
        for n in nets:
            assert n in known, f"net class {name}: unknown net {n}"
    pro = {
        "board": {"design_settings": {"defaults": {}, "rules": {   # kicad/layout_plan.md section 4
            "min_clearance": 0.15, "min_track_width": 0.15, "min_through_hole_diameter": 0.3, "min_via_diameter": 0.6,
            "min_via_annular_width": 0.15, "min_copper_edge_clearance": 0.5, "min_text_height": 1.0,
            "min_text_thickness": 0.15}}},
        "meta": {"filename": PROJECT + ".kicad_pro", "version": 1},
        "net_settings": {
            "classes": [cls("Default", 0.25, 0.2)] + [cls(k, v[0], v[1]) for k, v in classes.items()],
            "meta": {"version": 3}, "net_colors": None, "netclass_assignments": None,
            "netclass_patterns": [{"netclass": k, "pattern": n} for k, v in classes.items() for n in v[2]]},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[ROOT, ""]],
        "text_variables": {},
    }
    with open(os.path.join(HERE, PROJECT + ".kicad_pro"), "w", newline="\n") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")
    # Custom design rule: 0.5 mm around the switch node. A net class clearance cannot be used for SW, because
    # U1 pin 21 (SW) sits between pins 20 (TG) and 22 (BOOST) at 0.5 mm pitch (0.2 mm gap).
    with open(os.path.join(HERE, PROJECT + ".kicad_dru"), "w", newline="\n") as f:
        f.write('(version 1)\n\n'
                '(rule "SW copper 0.5 mm from other nets (not at the U1 pins)"\n'
                "  (condition \"A.NetName == 'SW' && A.Type != 'Pad' && !A.intersectsCourtyard('U1')\")\n"
                '  (constraint clearance (min 0.5mm)))\n')


if __name__ == "__main__":
    build()
    self_check()
    write_schematic()
    write_libs()
    write_project()
    print(f"schematic: {len(sch_symbols)} symbols ({len([s for s in sch_symbols if not flat(s[-1]).count('#')])} parts), "
          f"{len(sch_labels)} labels, {len(sch_wires)} wires, {len(sch_nc)} no-connect flags")
