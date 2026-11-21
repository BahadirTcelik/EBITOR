# KiCad project

Open `ee463_dcdc.kicad_pro` with KiCad 8, 9 or 10. Everything in this folder except the two Markdown plans is
generated from `netlist/schematic_netlist.py`, the single source of all components and connections.

| File | Content |
|---|---|
| `ee463_dcdc.kicad_sch` | schematic, one A3 sheet, 103 parts in five blocks. Connections are made with net labels; GND pins carry a GND symbol. Written in the KiCad 7 file format; newer versions convert it when saving |
| `ee463_dcdc.kicad_pro`, `ee463_dcdc.kicad_dru` | project file with the net classes and design rules of `layout_plan.md` section 4 (check them in Board Setup after the first save); custom rule for 0.5 mm around SW |
| `ee463_dcdc.kicad_pcb` | board, **placement only, not routed**: 100 × 70 mm, 4 layers, 103 footprints, draft pours, silkscreen. KiCad 7 file format plus the "do not populate" flag of the six DNP footprints, which needs KiCad 8 or newer (`out/ee463_dcdc_k7.kicad_pcb` is the same board without the flag) |
| `make_pcb.py` | board generator (pcbnew Python API): reads the schematic netlist, places the parts from its `PLACE` table, draws the draft pours and measures the placement distances. It refuses to overwrite a board that was changed after it wrote it (`--force` overrides) |
| `run_pcb_checks.bat` | KiCad DRC → `out\drc.rpt` and the course PCB-Checker (`..\PCB-Checker`, `--overload`) → `out\pcb_check.html` |
| `ee463.kicad_sym`, `sym-lib-table` | project symbol library: LTC3895 (31 leads + exposed pad, drawn in package order) |
| `ee463.pretty/`, `fp-lib-table` | project footprint library: LTC3895 FE38(31) with exposed pad and thermal vias; generic 2-position 5.00 mm terminal block |
| `make_kicad.py` | generator. Regenerating overwrites the schematic, so after editing the schematic by hand either stop regenerating or make the change in `netlist/schematic_netlist.py` |
| `run_kicad_checks.bat` | runs `kicad-cli`: ERC report, netlist, schematic PDF and a footprint-name check into `out/` |
| `ee463_dcdc_schematic_preview.pdf` | the schematic as plotted by kicad-cli 7.0.11 on 16 Nov 2026 (for reading without KiCad) |
| `compare_netlist.py` | compares `out/ee463_dcdc.net` with `netlist/pins.csv` |
| `footprints.md` | pin tables and footprints compared with the datasheets (16 Nov 2026) |
| `layout_plan.md` | floor plan as placed, measured distances, layer use, net classes and design rules, critical routes, check results, open points |
| `out/placement_checks.md`, `out/assembly_top.pdf`, `out/pcb_check_placement.html` | output of `make_pcb.py`; F.Fab drawing with all references; PCB-Checker report of the unrouted board (run without KiCad's DRC) |
| `pcb_checker.json` | PCB-Checker settings; keep it next to the project file |

## Status (17 Nov 2026)

- Schematic regenerated on 17 Nov (5 V rail of the current-limit circuit from the TL431, U5 and C32 removed, R30 added;
  assembly groups). Exported with `kicad-cli` 7.0.11: the netlist is identical to `netlist/pins.csv`
  (103 parts, 224 pads, 40 nets).
- **ERC of the new schematic has not been run** (KiCad 7's command line has no ERC): run `run_kicad_checks.bat` again.
  Result for the schematic of 16 Nov with KiCad 10.0.8: 0 errors, 6 warnings, all "symbol does not match the copy in the
  library" (Q1–Q3, U3, U4, RV1). The schematic holds copies of the KiCad 7 symbols; their pin numbers were checked
  against the datasheets. Do **not** run "Update Symbols from Library" without comparing the netlist again
  (`compare_netlist.py`). `+5V_CC` now carries a PWR_FLAG (it is fed through R29).
- Board placed by `make_pcb.py`, **not routed** (17 Nov). All placement distances of `layout_plan.md` section 2 are
  met; VIN pour 10.5 cm²; PCB-Checker on the unrouted board (without KiCad's DRC): 0 must fix, 2 should fix (4 layers;
  no test point on `VIN_IC`), 3 to check (thermal vias at Q1–Q3).
- KiCad 10.0.8 DRC of the board of 16 Nov: field `MPN` missing on the footprints, DNP flag missing, thermal reliefs at U1;
  all three are handled in `make_pcb.py` now (`layout_plan.md` section 7). The new board has not been checked with
  KiCad 10 yet (`run_pcb_checks.bat`).
- Do not press F8 for a first import: the footprints are already on the board. After a schematic change use
  `make_pcb.py` (before routing) or Tools → Update PCB from Schematic (after routing has started).
- Stack-up: 4 layers, 1.6 mm, 1 oz (sponsorship announcement: up to 200 × 200 mm, up to 4 layers); L2 is one GND zone.
  Check the layer thicknesses in Board Setup → Physical Stackup before ordering.
- Fabrication outputs (Gerber + drill) go to `fab/`; run PCB-Checker on the final submission zip.

## Regenerating

```
pip install sexpdata
set KICAD_SYMBOL_DIR=C:\Program Files\KiCad\10.0\share\kicad\symbols
python make_kicad.py
```

Board (Linux or the KiCad command prompt; needs `pcbnew` and `kicad-cli` 7 or newer):

```
python make_pcb.py
```
