"""Compare a netlist exported by KiCad (kicad-cli sch export netlist --format kicadsexpr) with netlist/pins.csv.

Usage: python compare_netlist.py [out/ee463_dcdc.net] [netlist/pins.csv]
Exit code 0 = identical. Uses only the standard library.
pins.csv is the design source (schematic_netlist.py); the KiCad netlist is what the PCB editor will receive.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
net_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out", "ee463_dcdc.net")
pins_file = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "netlist", "pins.csv")


def tokens(text):
    for m in re.finditer(r'\(|\)|"((?:[^"\\]|\\.)*)"|[^\s()"]+', text):
        t = m.group(0)
        yield ("str", m.group(1)) if t.startswith('"') else (t, t) if t in "()" else ("atom", t)


def parse(text):
    stack, cur = [], []
    for kind, val in tokens(text):
        if kind == "(":
            stack.append(cur)
            cur = []
        elif kind == ")":
            done, cur = cur, stack.pop()
            cur.append(done)
        else:
            cur.append(val)
    return cur[0]


def child(e, name):
    return [x for x in e if isinstance(x, list) and x and x[0] == name]


with open(net_file, encoding="utf-8") as f:
    tree = parse(f.read())

got, footprints, values = {}, {}, {}
for comp in child(child(tree, "components")[0], "comp"):
    ref = child(comp, "ref")[0][1]
    fp = child(comp, "footprint")
    footprints[ref] = fp[0][1] if fp else ""
    values[ref] = child(comp, "value")[0][1]
for net in child(child(tree, "nets")[0], "net"):
    name = child(net, "name")[0][1]
    if name.startswith("unconnected-"):
        name = "NC"
    name = name.lstrip("/")
    for node in child(net, "node"):
        got[(child(node, "ref")[0][1], child(node, "pin")[0][1])] = name

want, want_fp = {}, {}
with open(pins_file, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        for pad in row["Pads"].split():
            want[(row["Ref"], pad)] = row["Net"]

errors = []
for key in sorted(set(want) | set(got)):
    w, g = want.get(key), got.get(key)
    if w == g or (w == "NC" and g is None):
        continue
    errors.append(f"{key[0]} pad {key[1]}: pins.csv = {w}, KiCad = {g}")
refs_want = {k[0] for k in want}
missing_parts = sorted(refs_want - set(footprints))
no_fp = sorted(r for r, fp in footprints.items() if not fp)
nets_want = {n for n in want.values() if n != "NC"}
nets_got = {n for n in got.values() if n != "NC"}

print(f"KiCad netlist: {len(footprints)} parts, {len(got)} pads, {len(nets_got)} nets")
print(f"pins.csv     : {len(refs_want)} parts with pins, {len(want)} pads, {len(nets_want)} nets")
for title, items in (("Pad differences", errors), ("Parts missing in KiCad", missing_parts), ("Parts without footprint", no_fp),
                     ("Nets only in pins.csv", sorted(nets_want - nets_got)), ("Nets only in KiCad", sorted(nets_got - nets_want))):
    if items:
        print(f"{title} ({len(items)}):")
        for x in items:
            print("  -", x)
ok = not (errors or missing_parts or no_fp or nets_want ^ nets_got)
print("RESULT: netlist matches pins.csv" if ok else "RESULT: DIFFERENCES FOUND")
sys.exit(0 if ok else 1)
