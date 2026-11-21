# PCB layout plan and first placement (4 layers)

Status on 17 Nov 2026: **placement done, not routed.** `make_pcb.py` builds `ee463_dcdc.kicad_pcb` from the schematic
netlist (103 footprints, 40 nets). Draft pours exist; tracks, vias and the final pour shapes belong to the routing step.
Changes against the placement of 16 Nov: the current-limit circuit is one framed block (assembly group B), its 5 V rail
comes from the TL431 (U5 and C32 are gone, R30 is new), the VIN pour was extended to 10.5 cm², and the findings of the
first KiCad 10 design rule check were worked in (section 7).

Assumptions: **4 layers**, 1.6 mm, 1 oz copper. The sponsorship announcement allows boards up to 200 × 200 mm with
up to 4 layers (changed from 2 layers on 16 Nov 2026). No stencil: paste dispenser and reflow oven, or hand soldering.
Packages are 0805 or larger. All parts are on the top side. Outline **100 × 70 mm**, corner radius 3 mm, four M3 holes
4.5 mm from the edges. Component references follow `netlist/netlist_by_block.md`. Thresholds are those of the course
PCB-Checker (`pcbcheck/rules.py`).

## 1. Floor plan (as placed)

Board coordinates in mm, origin at the top left corner of the outline (the sheet origin is 50, 40 mm further up left).

```
 x: 0         20        40        60        80       100 mm
    +--------------------------------------------------+ y = 0
    | H1 TP2 Q3 C1 D3 R1    TP1   [VIN pour]  TP3   H2 |
    | J1   R2 R3         [ VIN pour ]  C3              | 10
    | (in)  group C                    C2    +------+  |
    |    C8                          Q1  Q2  |  L1  |RS1 C9| 20
    |  (bulk)   C7 C6 C5 C4          [ SW pour ]----+ ..C12|
    |    R4     R21 R9    row A (gate, supply parts)   | 30
    |                 C23 R10 [  U1  ]   TP9 TP10  C13 |
    | EE463 60 W BUCK     row B (signal parts)     C14 | 40  TP7
    | (title, group)      row C (signal parts, R25)    |
    |                           +-- CC (opsiyonel) ----+ 50
    |                      +----+ R24 D1 U3 C29 C28 U2 |RSH1
    |                      | TP19      C31 R23         | J2   (out)
    |                      | TP20 R28 R27 D2 C30 C33 R29     60
    | H3 TP4 TP11..TP14    | TP18  [RV1]   R26 U4 R30  | TP6 TP5 H4
    +----------------------+ TP21 ---------------------+ 70
```
(not to scale)

- Input at the left edge (J1, wires enter from the left), output at the right edge (J2, wires enter from the right).
- Q1 and Q2 sit side by side: Q1 turned 90° (drain tab up, in the VIN pour), Q2 turned 270° (sources up, to GND;
  drain down). The SW pour runs below both MOSFETs and ends at the left pad of L1. C2 and C3 bridge the VIN pour and
  the GND copper directly above the two MOSFETs, so the hot loop closes on the top layer without vias.
- U1 is turned 90°: pins 20–38 (TG, SW, BOOST, BG, DRVCC, EXTVCC, VIN, INTVCC) face up towards the MOSFETs, pins 1–19
  (sense, feedback, ITH, SS, FREQ) face down, away from SW and L1.
- **Group C** (reverse polarity: Q3, D3, R1, C1 and the bypass footprints R2, R3) sits next to J1 in the top left corner.
- **Group B** (current-limit circuit) is one block at the lower edge beside the shunt, inside a silkscreen frame with
  the text "CC (opsiyonel)" (section 6). Nothing of group A is inside the frame, so the basic converter can be
  soldered and reworked with the block empty.

Exact positions: table `PLACE` in `make_pcb.py`. Pictures: `out/assembly_top.pdf` (all references on F.Fab).

## 2. Placement order (as done) and measured distances

1. **Hot loop:** Q1, Q2, C2, C3; then C4–C7 along the lower edge of the VIN pour.
2. **L1** right of the SW pour; nothing else inside its courtyard.
3. **RS1**, output capacitors C9–C12 (column), C13, C14, then **RSH1** and **J2**.
4. **U1** below Q1/Q2 with its supply and gate parts in row A (y = 32.6 mm) and the signal parts in rows B and C
   (y = 44.7 and 48.9 mm).
5. Input side: J1, group C (Q3 with R1, D3, C1; R2/R3), bulk capacitor C8 with R4.
6. Group B block: U2 at RSH1, then towards the left R23, U3 with C30 / D2, D1, R24; the 5 V rail (R29, C33, U4, R26,
   R30) below U2; trimmer RV1 with R27 / R28; the four test points in a column at the left end.
7. Test points (8 in a row along the lower edge, the rest at their nets), mounting holes, silkscreen.

Measured by `make_pcb.py` on the generated board (`out/placement_checks.md`); "edge" = pad edge to pad edge:

| Check | Value (mm) | Limit (mm) |
|---|---|---|
| C2 VIN pad to Q1 drain pad / C2 GND pad to Q2 source pads (edge) | 1.42 / 1.78 | ≤ 5 |
| C3 VIN pad to Q1 drain pad / C3 GND pad to Q2 source pads (edge) | 4.72 / 4.84 | ≤ 5 |
| U1 TG pin 20 to Q1 gate pad (centres, straight line) | 10.36 | ≤ 15 |
| U1 BG pin 24 to Q2 gate pad (centres, straight line) | 14.87 | ≤ 15 |
| C22 to U1 BOOST pin 22 / SW pin 21 (edge) | 2.11 / 3.44 | ≤ 5 |
| R13 / R14 to U1 VFB pin 6 (edge) | 2.01 / 1.28 | ≤ 10 |
| C24 → DRVCC pin 26, C25 → INTVCC pin 38, C26 → VIN pin 30, C27 → EXTVCC pin 32 (edge) | 1.35, 1.49, 1.35, 1.82 | ≤ 4 |
| C28 → U2 pin 5, C29 → U3 pin 5 (5 V rail), C31 → U3 pin 3 (edge) | 0.55, 0.75, 1.15 | ≤ 4 |
| C33 (10 µF, 5 V rail) → U4 cathode pin 1 (edge) | 0.85 | ≤ 4 |
| C23 (10 µF) to U1 DRVCC pin 26 (edge) | 10.34 | – (bulk; C24 is the close one) |
| Courtyard overlaps; parts inside the L1 courtyard | none | none |
| Pads of different parts closer than 0.5 mm (same net included); pads closer than 0.5 mm to the edge | none | none |
| Mounting holes to the board edge; nearest pad to a hole centre | 4.5; 5.1 (TP2 at H1) | ≥ 4; ≥ 4 |
| VIN copper on L1 (Q1 drain pour) | 1048 mm² = 10.5 cm² | ≥ 10 cm² |

Notes on the table:
- The gate distances are straight lines. The real gate paths go through R5 / R6 and cross the SW pour on L3
  (section 5), about 17 mm (TG) and 15 mm (BG) before routing detours; the BG value has no margin.
- VIN copper: the pour was extended along the top edge to x = 78 mm (above L1) to reach the target; the added strip is
  up to 30 mm away from Q1 and cools less than copper next to the MOSFET. A further 8.0 cm² VIN area lies on L4 under
  it; it counts only after the stitching vias next to Q1 are placed (routing step).
- Kelvin lines of the shunt: U2 pin 3 (IN+) is 5.5 mm and pin 4 (IN−) 7.7 mm (centres) from the RSH1 pads. Pin 4 lies on
  the far side of U2: its track passes between the pad rows under U2 or changes to L3.

## 3. Layers

| Layer | Use |
|---|---|
| L1 top | all components; pours for VIN, SW, SNS_P, VOUT_C, VOUT; local GND for the hot loop; gate drive and short signals |
| L2 inner | GND plane, **unbroken**: no tracks on this layer |
| L3 inner | signals that do not fit on L1 (gate hops under the SW pour, sense and feedback pairs, CC loop), DRVCC / EXTVCC / +5V_CC; GND fill elsewhere |
| L4 bottom | GND pour; second copper for VIN (under Q1) and VOUT (under the output capacitors) stitched to L1 for heat and current |

- Power current stays on the outer layers (L1, L4). An inner layer needs about 2.6 times the width for the same
  temperature rise (PCB-Checker rule), so no power path is routed on L2 or L3.
- Q1 drain (VIN) pour: 10.5 cm² on L1 as placed (target 10 cm²), plus 8.0 cm² on L4; thermal vias beside the drain pad join the two.
- Under L1 (the inductor): no tracks on any layer; GND copper is allowed.
- U1 exposed pad: 3 × 3 array of 0.3 mm vias (in the footprint) to the L2 GND plane and the L4 pour.
- Stitch L1 and L4 GND areas to the L2 plane with vias near C2/C3, the output capacitors and J1/J2.
- KiCad: Board Setup → Physical Stackup → 4 copper layers; set L2 to type "power plane" and fill it with one GND zone.
- Fallback to 2 layers (if the course team later limits the sponsored round): L4 takes the role of L2, the L3 signals
  move to L1 or become short jumpers on the bottom; the floor plan does not change.

## 4. Net classes

Track widths from IPC-2221, external layer, 1 oz, 20 K rise (the checker's criterion).

| Class | Nets | Current | Minimum width | Use |
|---|---|---|---|---|
| PWR_IN | VIN, VIN_RTN, CBULK_N | 4.74 A (90 W at 20 V) | 1.7 mm | pours; any neck ≥ 2.5 mm |
| PWR_OUT | SW, SNS_P, VOUT_C, VOUT | 7.5 A (overload) | 3.2 mm | pours; any neck ≥ 4 mm |
| GND | GND | 7.5 A | – | L2 plane + L1 / L4 pours |
| GATE | TG, TG_G, BG, BG_G, BOOST | pulses of 2–4 A | 0.5 mm | ≤ 15 mm from U1 to gate, ≤ 30 mm per net |
| AUX | DRVCC, EXTVCC, VIN_IC, +5V_CC, INTVCC | < 50 mA | 0.4 mm | |
| SIGNAL | everything else | – | 0.25 mm | |

Design rules in `ee463_dcdc.kicad_pro` (Board Setup → Constraints) and `ee463_dcdc.kicad_dru`:

| Rule | Value |
|---|---|
| Minimum track width / clearance | 0.15 mm / 0.15 mm |
| Minimum hole | 0.30 mm |
| Via | 0.6 mm pad / 0.3 mm drill (annular ring 0.15 mm) |
| Copper to board edge | 0.5 mm (pours are drawn 0.7 mm inside the outline) |
| Net class clearance | 0.2 mm; **0.5 mm for VIN, VIN_RTN, CBULK_N** (class PWR_IN) |
| SW | 0.5 mm from other nets by a custom rule (tracks and pours, not pads; not inside the U1 courtyard) |
| Silkscreen text | ≥ 1.0 mm high, 0.15 mm line |

- SW cannot have a 0.5 mm net class clearance: U1 pin 21 (SW) lies between pins 20 and 22 at 0.5 mm pitch. The custom
  rule was loaded without error by KiCad 7; its effect can only be seen once SW tracks exist.
- Vias: about 0.5 A each. A 7.5 A layer change needs 15; use 20. Avoid layer changes in the power path altogether.

## 5. Critical routes

| Route | Rule |
|---|---|
| RS1 → U1 pins 3, 4 | parallel pair, Kelvin, away from SW, L1 and the gate tracks; nothing in series with pin 4 |
| RSH1 → U2 pins 3, 4 | Kelvin from the inside of the pads, pair ≤ 15 mm |
| VOUT → R15 → R13 → VFB | start at J2 (after the shunt); ≥ 1 mm from SW copper (aim for ≥ 5 mm); divider ≤ 10 mm from pin 6 |
| TG / SW and BG / GND | The SW pour lies between U1 and both gate pads, so each gate net crosses it on **L3** (two vias per net, 0.5 mm track, GND plane on L2 directly above). Alternative: a 1 mm gap in the SW pour is not used, it would cut the 7.5 A path |
| BOOST capacitor | ≤ 5 mm from pins 21–22, same side, no vias |
| Decoupling capacitors | ≤ 4 mm from their pins (edge to edge) |
| ITH | short node; the CC link R25 and D1 close to pin 7; keep away from SW |

## 6. Assembly groups, the CC block and test points

| Group | Parts | Where |
|---|---|---|
| A basic converter | everything else, including RSH1 and J2 | – |
| B current-limit loop (optional at the first assembly) | U2, U3, U4, RV1, D1, D2, R23, R24, R26–R30, C28–C31, C33, TP18–TP21; R25 | framed block, x = 46–83 mm, y = 48.3–68.8 mm (L-shaped); **R25** (0 Ω link) stays at the ITH pin of U1 in row C |
| C reverse-polarity protection | Q3, D3, R1, C1 (R2, R3: bypass, fitted only without Q3) | top left corner beside J1 |

- R25 is outside the frame on purpose: with group B unpopulated nothing but the pad of R25 hangs on ITH. The `CC_LINK`
  track from R25 to R24 is 8 mm long (straight line).
- DRVCC reaches R29 (right end of the block) on L3; 6 mA.
- Without group B: do not fit R25. Without group C: fit R2 and R3.

21 loop test points: GND ×3 (TP3 top right, TP4 lower left, TP5 next to J2), VIN, VIN_RTN, VOUT, VOUT_C, SW, TG_G, BG_G,
DRVCC, INTVCC, EXTVCC, ITH, PGOOD, SS, FB_TOP and, inside the CC block, VREF_CC, CC_OUT, ISENSE, +5V_CC. The silkscreen
shows the net name at each one. Output ripple: probe between TP6 (VOUT) and TP5 (GND), 7.8 mm apart (the plan was 5 mm
across C12). Not present: `VIN_IC` (section 9).

## 7. Checks

1. `python make_pcb.py` – placement distances (section 2), written to `out/placement_checks.md`.
2. `run_pcb_checks.bat` (Windows, KiCad 8–10): KiCad DRC → `out\drc.rpt`; course PCB-Checker with `--overload`
   → `out\pcb_check.html`. `pcb_checker.json` next to the project sets `overload: true` and the net roles.
3. Fix every red item; fix or justify (waiver with a reason) every orange item.

**KiCad 10.0.8 DRC of the board of 16 Nov** (run on the PC, 16 Nov 20:30) and what was done about it:

| Finding | Count | Action in `make_pcb.py` (17 Nov) |
|---|---|---|
| Footprint lacks the symbol field `MPN` | 104 | field written to every footprint |
| "Do not populate" differs between symbol and footprint | 6 | flag written into the board file (KiCad 7 cannot store it: `mark_dnp()`) |
| Thermal relief incomplete at U1 (exposed pad, its vias, GND pins 9, 12, 13, 15) | 16 | these pads now connect solidly to the GND zones |
| Footprint does not match the library copy (KiCad 7 footprints, KiCad 10 library) | 67 | warnings, left as they are |
| Unconnected pads | 98 | expected: the board is not routed |

The new board has **not** been checked with KiCad 10 yet.

PCB-Checker on the new board (run in the cloud without KiCad's DRC, 17 Nov): **0 must fix, 2 should fix, 3 to check**
(`out/pcb_check_placement.html`):

| Finding | Plan |
|---|---|
| 4 copper layers "may not be covered by the sponsored round" | justify: the sponsorship announcement states "up to 4 layers" |
| No test point on `VIN_IC` | decision open (section 9); the `LDO_IN` finding of 16 Nov disappeared with the LDO |
| No thermal vias at Q1, Q2, Q3 pad 5 (to check) | add in the routing step |

DRC with KiCad 7 (pcbnew, in the cloud): no clearance, edge or silkscreen violations; unconnected pads (not routed);
three "thermal relief incomplete" warnings at GND pads of row A (C25, C26, C27) – GND vias beside the pads in the routing step.

## 8. Checklist before sending the board

- [ ] Footprints checked 1:1 on paper: U1 (TSSOP-38, 31 leads, exposed pad), Q1–Q3, L1, C8, C13/C14, J1/J2, RV1
- [x] C8 (12.5 mm can) and C13/C14 (8 × 6.7 mm) compared with the manufacturer drawings (16 Nov)
- [ ] J1/J2: generic 5.00 mm terminal block bought and laid on the 1:1 print (pitch, pin size, body outline)
- [ ] Assembly without stencil planned: paste dispensed for Q1–Q3, U1 (leads and exposed pad), L1, C13/C14; reflow; then hand soldering of the rest
- [x] Pin numbers of U2 (INA180 A pinout), U3 (MCP6001 standard pinout), U4 (TL431 DBZ) checked against datasheets
- [ ] Capacitor voltage written in every Value field (input ≥ 63 V, output ≥ 16 V)
- [ ] Pads of different parts ≥ 0.5 mm apart; no part smaller than 0805
- [ ] No vias in small SMD pads; thermal vias only in pads larger than 4 mm²
- [ ] ERC and DRC clean; pours refilled; no acute angles or stubs
- [ ] All DNP parts marked (R2, R3, R7, C15, C18, R18)

## 9. Open points after placement

- **Board size:** 100 × 70 mm as requested. The lower left quarter carries only the title and the test point row;
  a smaller outline is possible but needs the test point row and the title moved (not tried).
- **Gate nets on L3** (section 5): accepted for the first routing attempt; BG pin-to-gate distance is 14.87 mm.
- **Place of the CC block:** lower edge, left of the shunt and of J2. Its left part (x = 46–59 mm) holds only the four
  test points; the block can be made shorter if the test points move.
- **Silkscreen references:** only for parts larger than 1210. Chip parts have their reference on F.Fab
  (`out/assembly_top.pdf`); use that drawing for assembly.
- **Test point for `VIN_IC`:** the checker asks for one on every auxiliary supply. The net is VIN behind R21 (4.7 Ω);
  adding TP22 changes the schematic, netlist and BOM.
- **Silkscreen "GROUP __":** group number missing.
- Footprints from KiCad 7 libraries: KiCad 10 reports "footprint does not match library" warnings.
