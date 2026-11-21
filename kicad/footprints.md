# Footprints and pinouts

Source of the assignments: `netlist/schematic_netlist.py` (field `fp`, exported to `bom/ee463_bom.csv`, and the
function `pads()` that maps each pin to KiCad pad numbers). The KiCad schematic is generated from the same file.

**Status (16 Nov 2026): pin numbers of all ICs, MOSFETs and polarised parts were compared with the datasheets.**
Ten PDFs supplied by the team were read: the pin configuration and the package drawing of the LTC3895 (official
Rev A, `3895fa.pdf`), the Panasonic FC and the KEMET A768 data sheets were added in a second pass on the same day,
which closed the rows that were marked "check". The terminal block is now a generic 5.00 mm part without a fixed
type, so its row stays open until the part is bought. Footprint geometry was compared with the KiCad 7.0.11
library; `run_kicad_checks.bat` confirmed with KiCad 10.0.8 that every footprint name exists in the installed
library (`out/footprint_check.txt`, 19 of 19 at the first run).
A 1:1 paper print of U1, Q1–Q3, L1, C8, C13/C14 and J1/J2 is still required before the board is ordered.

## 1. Pin tables compared with the datasheets

| Part | Pins used in the netlist (pad → function → net) | Datasheet, revision, page | Result |
|---|---|---|---|
| U1 LTC3895EFE | 1 OVLO, 2 VPRG (NC), 3 SENSE+, 4 SENSE−, 5 SS, 6 VFB, 7 ITH, 8 MODE, 9 GND, 10 CPUMP_EN, 11 CLKOUT (NC), 12 GND, 13 PLLIN, 14 PGOOD, 15 GND, 16 NC, 17 FREQ, 18 DRVSET, 19 DRVUV, 20 TG, 21 SW, 22 BOOST, 24 BG, 26 DRVCC, 28 NDRV, 30 VIN, 32 EXTVCC, 34 RUN, 36 PHASMD, 37 ILIM, 38 INTVCC, 39 exposed pad = GND | LTC3895 Rev A (3895fa, LT 0916): pin configuration figure p. 2, pin functions pp. 9–11 | **matches**, all 31 leads and the pad. Leads 23, 25, 27, 29, 31, 33, 35 do not exist |
| Q1 BSC070N10NS5 | 1, 2, 3 source; 4 gate; 5, 6, 7, 8 drain | Infineon Rev. 2.1 (2015-07-13), p. 2 | **matches** |
| Q2, Q3 BSC040N10NS5 | same | Infineon Rev. 2.1 (2015-01-07), p. 2 | **matches** |
| U2 INA180A2IDBVR | 1 OUT, 2 GND, 3 IN+, 4 IN−, 5 VS | TI SBOS741H (July 2022), p. 4, figure 6-1 "pinout A" | **matches**. The INA180**B** has IN+ on 1, IN− on 3, OUT on 4: do not substitute |
| U3 MCP6001T-E/OT | 1 VOUT, 2 VSS, 3 VIN+, 4 VIN−, 5 VDD | Microchip DS21733F (2005), p. 1 | **matches**. MCP6001R (VDD on 2, VSS on 5) and MCP6001U (VIN+ on 1, VOUT on 4) differ |
| U4 TL431AIDBZR | 1 cathode, 2 REF, 3 anode | TI SLVS543J (Dec 2005), p. 1, DBZ package | **matches**. The TL432 has REF on 1 and cathode on 2 |
| D1, D2, D3 | pad 1 cathode, pad 2 anode | KiCad convention of `D_SOD-123` | netlist uses the same convention |
| C8, C13, C14 | pad 1 plus, pad 2 minus | KiCad convention of the `CP_*` footprints | netlist uses the same convention |

Two of the supplied PDFs are old revisions (MCP6001 from 2005, TL431 from 2005). Download the current revisions for
the report bibliography.

KiCad cross-check: the KiCad library symbols `INA180A2`, `MCP6001-OT`, `TL431DBZ`, `HT75xx-1-SOT89`,
`BSC070N10NS5` and `BSC040N10NS5` carry the same pin numbers as the datasheets, and the schematic uses these symbols.

## 2. Changes made after the datasheet check

| # | Finding | Change |
|---|---|---|
| 1 | KiCad's `TDSON-8-1` footprint has pads 1–4 and one pad **5** that covers leads 5–8 and the tab (the KiCad symbols of both MOSFETs use pin 5 for the drain) | pad map of Q1–Q3 in the netlist: S → 1, 2, 3; G → 4; D → 5 |
| 2 | EEU-FC2A101 is a 12.5 × 20 mm can with 5.0 mm lead spacing, not 10 mm as assumed (the 10 × 30 mm part is EEUFC2A101L). Data sheet: 0.180 Ω at 100 kHz, 671 mA ripple | C8 footprint changed to `CP_Radial_D12.5mm_P5.00mm` |
| 3 | A768KE107M1VLAE036 is an 8 × 6.7 mm can on an 8.3 × 8.3 mm base (case KE); 36 mΩ, 1.4 A ripple | C13, C14 footprint set to `CP_Elec_8x6.7` |
| 4 | Würth 74435561100: DCR is 6.9 mΩ **±8 %** (7.45 mΩ max), not "6.9 mΩ max"; saturation current is 10 A for −10 % and 21.5 A for −30 % inductance | BOM text corrected. Effect on losses: +17 mW at 5 A, +37 mW at 7.5 A (with the 1.2 hot factor); `calc/` not re-run, so the loss tables in the report still use 6.9 mΩ |
| 5 | LTC3895 package FE38(31) is not in the KiCad library | project footprint `ee463.pretty/LTC3895_TSSOP-38-31-1EP_…` generated (section 4) |
| 6 | Terminal block: the team will buy a cheaper generic 5.00 mm block instead of Würth 691137710002 | BOM rows of J1, J2 made generic; project footprint with 1.5 mm holes so that the pin size of the final part is not critical |
| 7 | C8 impedance is 0.180 Ω and its ripple rating 671 mA (data sheet). The input-filter calculation (T09) wanted 0.3–0.6 Ω for damping and gave 0.62 A in the bulk capacitor at 0.2 Ω | **open, not changed**: fit R4 = 0.22–0.33 Ω (2512) instead of 0 Ω, as the note on R4 already says for an ESR below 0.2 Ω. To be decided with the second order batch |

## 3. Footprints

| Parts | Footprint | Compared with | Result |
|---|---|---|---|
| U1 | `ee463:LTC3895_TSSOP-38-31-1EP_4.4x9.7mm_P0.5mm_EP2.74x4.75mm_ThermalVias` | LTC drawing 05-08-1865 Rev B (datasheet Rev A p. 36) | **matches** the recommended solder pad layout, see section 4; 1:1 print before ordering |
| Q1, Q2, Q3 | `Package_TO_SOT_SMD:TDSON-8-1` | outline PG-TDSON-8, Infineon Rev. 2.1 p. 11 (the datasheet has no land pattern) | pitch 1.27 mm matches; pad span 6.65 mm against 5.95–6.35 mm over the leads; drain pad 4.55 × 4.41 mm. Consistent with the outline; **check** on a 1:1 print |
| L1 | `Inductor_SMD:L_Wuerth_HCI-1890` | Würth 74435561100 rev. 004.001 (2025-02-06), p. 1, recommended land pattern | **matches exactly**: two 6.0 × 6.0 mm pads, 7.3 mm apart |
| C8 | `Capacitor_THT:CP_Radial_D12.5mm_P5.00mm` (1.2 mm drill) | Panasonic FC series data sheet (Nov. 2012), dimensions p. 1, EEUFC2A101 row p. 10 | **matches**: can 12.5 × 20 mm, lead spacing 5.0 mm, lead diameter 0.6 mm |
| C13, C14 | `Capacitor_SMD:CP_Elec_8x6.7` (pads 4.0 × 2.5 mm, 2.1 mm apart, 10.1 mm over the pads) | KEMET A4088_A768 (2026-02-26): case KE p. 3, landing pad p. 10 | **usable, not identical**: KEMET recommends pads 4.2 × 2.2 mm, 3.1 mm apart (11.5 mm over the pads). The terminals (3.1 mm apart, 9.0 mm overall) sit fully on the KiCad pads with 0.5 mm of pad beyond each terminal end |
| J1, J2 | `ee463:TerminalBlock_Generic_1x02_P5.00mm_Drill1.5mm` (project footprint: 5.00 mm pitch, 1.5 mm holes, 2.8 mm pads) | no data sheet: the Würth 691137710002 was dropped on 16 Nov for a cheaper generic block with 5.00 mm pitch | **check** when the part is bought: pitch 5.00 mm (5.08 mm also fits), pins up to 1.0 × 1.0 mm, rating ≥ 10 A, body within the 10 × 8 mm outline |
| U2, U3 | `Package_TO_SOT_SMD:SOT-23-5` | standard numbering | fits the pin tables above |
| U4 | `Package_TO_SOT_SMD:SOT-23` | pads 1 and 2 on one side, 3 opposite | fits the DBZ pinout |
| RV1 | `Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical` | pad 2 = wiper | not compared with a Bourns datasheet |
| 0805 / 1206 / 1210 / 2512 parts, SOD-123, test points, M3 holes | KiCad standard footprints | – | no check needed beyond the 1:1 print of the 2512 parts |

## 4. LTC3895 footprint (generated by `make_kicad.py`)

Values from the "recommended solder pad layout" of the package drawing FE38 (AB), LTC DWG 05-08-1865 Rev B,
data sheet Rev A page 36 (read on the drawing itself).

| Feature | Datasheet | Footprint |
|---|---|---|
| Lead pitch | 0.50 mm | 0.50 mm |
| Pad size | 0.315 ± 0.05 × 1.05 ± 0.10 mm | 0.30 × 1.05 mm (0.20 mm between pads) |
| Over the two pad rows | 6.60 ± 0.10 mm (4.50 mm inside) | 6.60 mm (4.50 mm inside) |
| Exposed pad | 2.74 × 4.75 mm | 2.74 × 4.75 mm on top and bottom copper |
| Removed leads | 23, 25, 27, 29, 31, 33, 35 | no pads at these positions |
| Thermal vias | not specified | 3 × 3, 0.3 mm drill, 0.6 mm pad (PCB-Checker minimum drill 0.30 mm, annular ring 0.15 mm) |

The solder paste of the exposed pad is split into four windows between the via rows. The bottom pad has an open solder
mask so that the pad can be soldered by hand through the vias.

## 5. Other datasheet values that the design relies on

| Value | Datasheet | Design |
|---|---|---|
| INA180 common-mode range | −0.2 V to 26 V (SBOS741H p. 7) | 12 V |
| INA180 supply | 2.7 V to 5.5 V | 5.01 V (4.94–5.09 V) from the TL431 shunt regulator U4 |
| MCP6001 supply | 1.8 V to 6.0 V (DS21733F) | same rail |
| TL431A minimum cathode current | 0.4 mA typical, 0.7 mA maximum (TL431AI, SLVS543J) | ≥ 1.38 mA at DRVCC = 7.0 V, 5.3 mA at 10 V (R29 = 820 Ω; `calc/t12b_cc_supply.py`) |
| TL431 stability with a capacitive load | figure 16 (SOT-23, VKA = 5 V): unstable between about 0.007 µF and 3 µF | C33 = 10 µF on the rail: always fit it together with U4 |
| BSC070N10NS5 | 7.0 mΩ max, QG 30 nC, Qoss 41 nC (p. 2) | `calc/buck_losses.py`: 6.0 mΩ typical × 1.5 hot, 30 nC, 41 nC |
| BSC040N10NS5 | 4.0 mΩ max, QG 58 nC, Qoss 75 nC (p. 2) | `calc/buck_losses.py`: 3.4 mΩ typical × 1.5 hot, 58 nC, 75 nC |

## 6. Course constraints (sponsorship announcement) against this design

| Constraint | Design | Status |
|---|---|---|
| 0805 or bigger recommended; 0603 only for a few parts; no 0402 | chip parts: 0805 (43), 1206 (3), 1210 (10), 2512 (5); nothing smaller than 0805 | met |
| No stencil; soldering by the team (reflow oven, paste dispenser) | parts with pads under the body: Q1–Q3 (TDSON-8), U1 exposed pad, L1, C13/C14. U1 has 0.5 mm lead pitch: dispense paste or drag-solder. The exposed pad of U1 can also be soldered from the bottom through the vias | plan the assembly order in `layout_plan.md` |
| Board at most 200 × 200 mm | target outline about 100 × 70 mm | met |
| Up to 4 layers | 4 layers planned (`layout_plan.md` section 3) | met; PCB-Checker will print an orange stack-up note for more than 2 layers |
| Compactness bonus by volume | not targeted | – |

## 7. Change of 17 Nov 2026: 5 V rail from the TL431

U5 (HT7550-1), C32 and the 2.495 V reference node were removed. U4 (TL431AIDBZR, same footprint and pinout as before) now
regulates the 5 V rail: cathode on `+5V_CC`, REF on the midpoint of R26 / R30 (2 × 10 k 0.1 %), anode on GND; R29 = 820 Ω
feeds the rail from DRVCC. No new footprint type; `Package_TO_SOT_SMD:SOT-89-3` is no longer used. The schematic has
103 parts, 224 pads and 40 nets.
