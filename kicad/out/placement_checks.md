# Placement checks (make_pcb.py)

| Check | Value (mm) | Limit | Result |
|---|---|---|---|
| C2 VIN pad to Q1 drain pad (edge) | 1.42 | <= 5 | ok |
| C2 GND pad to Q2 source pads (edge) | 1.78 | <= 5 | ok |
| C3 VIN pad to Q1 drain pad (edge) | 4.72 | <= 5 | ok |
| C3 GND pad to Q2 source pads (edge) | 4.84 | <= 5 | ok |
| U1 TG pin 20 to Q1 gate pad (centres) | 10.36 | <= 15 | ok |
| U1 BG pin 24 to Q2 gate pad (centres) | 14.87 | <= 15 | ok |
| C22 to U1 BOOST pin 22 (edge) | 2.11 | <= 5 | ok |
| C22 to U1 SW pin 21 (edge) | 3.44 | <= 5 | ok |
| R13 to U1 VFB pin 6 (edge) | 2.01 | <= 10 | ok |
| R14 to U1 VFB pin 6 (edge) | 1.28 | <= 10 | ok |
| C24 to U1 pin 26 DRVCC (edge) | 1.35 | <= 4 | ok |
| C25 to U1 pin 38 INTVCC (edge) | 1.49 | <= 4 | ok |
| C26 to U1 pin 30 VIN_IC (edge) | 1.35 | <= 4 | ok |
| C27 to U1 pin 32 EXTVCC (edge) | 1.82 | <= 4 | ok |
| C28 to U2 pin 5 +5V_CC (edge) | 0.55 | <= 4 | ok |
| C29 to U3 pin 5 +5V_CC (edge) | 0.75 | <= 4 | ok |
| C31 to U3 pin 3 VREF_CC (edge) | 1.15 | <= 4 | ok |
| C33 to U4 pin 1 +5V_CC (edge) | 0.85 | <= 4 | ok |
| C23 (10 uF) to U1 DRVCC pin 26 (edge) | 10.34 | <= 30 | ok |

Footprints: 103, nets: 44, pads with a net: 234
Courtyard overlaps: none
Pads closer than 0.5 mm to the board edge: none
Pads of different parts closer than 0.5 mm (same net included): none
H1: 4.5 mm from the edge; nearest pad TP2 at 5.1 mm from the hole centre
H2: 4.5 mm from the edge; nearest pad C9 at 15.7 mm from the hole centre
H3: 4.5 mm from the edge; nearest pad TP4 at 6.5 mm from the hole centre
H4: 4.5 mm from the edge; nearest pad J2 at 6.2 mm from the hole centre
VIN copper on the top layer (Q1 drain pour): 1047 mm2 = 10.5 cm2 (target 10 cm2)
Filled copper per zone (mm2): GND B.Cu: 5451, GND F.Cu: 4361, GND In1.Cu: 6530, SNS_P F.Cu: 54, SW F.Cu: 125, VIN B.Cu: 800, VIN F.Cu: 1047, VIN_RTN F.Cu: 123, VOUT F.Cu: 53, VOUT_C B.Cu: 190, VOUT_C F.Cu: 202
