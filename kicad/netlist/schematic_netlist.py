"""Single source for the schematic: every component with its pin-to-net connections.

Running this file checks the connectivity and regenerates
  - kicad/netlist/netlist_by_block.md   (what to draw in KiCad, block by block)
  - kicad/netlist/pins.csv              (Ref, Pin, Pin name, Net)
  - kicad/netlist/nets.csv              (Net -> all pins on it)
  - bom/ee463_bom.csv                   (bill of materials with supplier data, 16 Nov 2026)
Net names VIN, VOUT, GND, SW follow the PCB-Checker convention. NC = intentionally not connected.
Pin numbers of ICs were checked against the datasheets on 16 Nov 2026 (see kicad/footprints.md).

17 Nov 2026: the 5 V supply of the current-limit circuit is a TL431 shunt regulator fed from DRVCC (CC_SUPPLY below;
calc/t12b_cc_supply.py). Every part belongs to an assembly group: A = basic converter, B = current-limit loop,
C = reverse-polarity protection (GROUP_B, GROUP_C below; BOM column "Assembly group").
"""
import csv
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
C = []  # components
CC_SUPPLY = "TL431_SHUNT"   # "TL431_SHUNT" (17 Nov) or "HT7550_LDO" (design until 16 Nov, kept so that it can be restored)


def add(ref, value, desc, pins, block, mpn="", sup="", stock="", price="", fp="", fit=True, note=""):
    C.append(dict(ref=ref, value=value, desc=desc, pins=pins, block=block, mpn=mpn, sup=sup,
                  stock=stock, price=price, fp=fp, fit=fit, note=note))


EK, OZ = "e-komponent", "Ozdisan / e-komponent"
OWN, OVS, GEN = "own stock, 1-3 working days", "overseas stock, 7-10 working days", "generic part: pick any equivalent in stock"
R0805, C0805 = "Resistor_SMD:R_0805_2012Metric", "Capacitor_SMD:C_0805_2012Metric"
R2512, C1210 = "Resistor_SMD:R_2512_6332Metric", "Capacitor_SMD:C_1210_3225Metric"
TPF = "TestPoint:TestPoint_Loop_D2.50mm_Drill1.0mm"
TB = "ee463:TerminalBlock_Generic_1x02_P5.00mm_Drill1.5mm"   # project footprint: any 2-pos 5.00 mm block (5.08 mm also fits)
TBD = "Screw terminal block 2-pos, 5.00 mm pitch, >= 10 A (15 A preferred), >= 60 V, pins up to 1.0 x 1.0 mm"
TBN = "generic part, chosen by price (16 Nov); check pitch, pin size and current rating of the part that is bought"
FET = "Package_TO_SOT_SMD:TDSON-8-1"          # KiCad pads: 1-3 source, 4 gate, 5 drain (pad 5 covers leads 5-8 and the tab)


def r(ref, val, a, b, block, mpn="", stock=GEN, price="", fit=True, note="", fp=R0805, sup=OZ, desc=None):
    add(ref, val, desc or f"Resistor {val} 1 % 0805", {"1": a, "2": b}, block, mpn, sup, stock, price, fp, fit, note)


def c(ref, val, a, b, block, mpn="", stock=GEN, price="", fit=True, note="", fp=C0805, sup=OZ, desc=None):
    add(ref, val, desc or f"Capacitor {val} 0805", {"1": a, "2": b}, block, mpn, sup, stock, price, fp, fit, note)


# ---------------------------------------------------------------- 1 input, reverse polarity
B = "1 Input and reverse polarity protection"
add("J1", "Input 20-48V", TBD, {"1": "VIN", "2": "VIN_RTN"}, B, "", OZ, GEN, "",
    TB, note=TBN + "; 4.7 A at 20 V and 90 W")
add("Q3", "BSC040N10NS5", "100 V N-MOSFET 4 mOhm (Q2 low side, Q3 reverse polarity switch in the return lead)",
    {"S": "GND", "G": "RP_GATE", "D": "VIN_RTN"}, B, "BSC040N10NS5ATMA1", EK, OWN, "249.81",
    FET, note="source to board GND, drain to the negative input terminal")
r("R1", "100k", "VIN", "RP_GATE", B, "RC0805FR-07100KL", OVS, "7.24", sup=EK)
add("D3", "12V zener", "Zener 12 V 0.4 W SOD-123, gate clamp", {"K": "RP_GATE", "A": "GND"}, B, "BZT52C12-HE3-08", EK, OVS, "17.65",
    "Diode_SMD:D_SOD-123")
c("C1", "100nF 50V", "RP_GATE", "GND", B, "CL21B104KBCNNNC", OVS, "7.24", sup=EK)
r("R2", "0R 2512", "VIN_RTN", "GND", B, "RC2512JK-070RL", OVS, "17.38", fit=False, fp=R2512, sup=EK, desc="0 ohm jumper 2512",
  note="DNP: bypass of Q3")
r("R3", "0R 2512", "VIN_RTN", "GND", B, "RC2512JK-070RL", OVS, "17.38", fit=False, fp=R2512, sup=EK, desc="0 ohm jumper 2512",
  note="DNP: bypass of Q3 (second in parallel)")
for i in range(6):
    c(f"C{2+i}", "4.7uF 100V", "VIN", "GND", B, "CL32B475KCVZW6E", OVS, "86.16", fp=C1210, sup=EK,
      desc="Ceramic 4.7 uF 100 V X7R 1210", note="C2, C3 within 5 mm of Q1 drain / Q2 source; C6, C7 may stay unpopulated at first" if i == 0 else "")
add("C8", "100uF 100V", "Aluminium electrolytic 100 uF 100 V, radial 12.5x20 mm, lead spacing 5 mm", {"+": "VIN", "-": "CBULK_N"}, B, "EEU-FC2A101", EK, OVS,
    "110.06", "Capacitor_THT:CP_Radial_D12.5mm_P5.00mm",
    note="can is 12.5 mm (distributor data), not 10 mm; 0.18 ohm impedance and 0.67 A ripple at 100 kHz (distributor data): confirm in the Panasonic datasheet")
r("R4", "0R 2512", "CBULK_N", "GND", B, "RC2512JK-070RL", OVS, "17.38", fp=R2512, sup=EK, desc="0 ohm jumper 2512 (damping resistor position)",
  note="replace by 0.22-0.33 ohm if the bulk capacitor ESR is below 0.2 ohm")

# ---------------------------------------------------------------- 2 power stage
B = "2 Power stage"
add("Q1", "BSC070N10NS5", "100 V N-MOSFET, high side", {"S": "SW", "G": "TG_G", "D": "VIN"}, B, "BSC070N10NS5ATMA1", EK, OVS, "169.43", FET,
    note="alternative: BSC040N10NS5 (same footprint): at 48 V the Q1 loss is 2.10 W at 60 W and 2.47 W at 90 W instead of 1.62 / 1.86 W, "
         "i.e. +105 K / +123 K instead of +81 K / +93 K at 50 K/W, and the average 60 W efficiency falls from 96.62 to 96.03 % "
         "(calc/q1_alternative.py); >= 10 cm2 copper on the drain (VIN) pour")
add("Q2", "BSC040N10NS5", "100 V N-MOSFET 4 mOhm (Q2 low side, Q3 reverse polarity switch in the return lead)", {"S": "GND", "G": "BG_G", "D": "SW"}, B, "BSC040N10NS5ATMA1", EK, OWN, "249.81", FET)
r("R5", "0R", "TG", "TG_G", B, "RC0805JR-070RL", OVS, "7.24", sup=EK, desc="0 ohm link 0805 (gate resistors, option links)", note="option 2.2-4.7 ohm against ringing")
r("R6", "0R", "BG", "BG_G", B, "RC0805JR-070RL", OVS, "7.24", sup=EK, desc="0 ohm link 0805 (gate resistors, option links)")
add("L1", "10uH", "Power inductor WE-HCI 1890, Isat 10 A (-10 %) / 21.5 A (-30 %), DCR 6.9 mOhm +-8 %", {"1": "SW", "2": "SNS_P"}, B, "74435561100", EK, OWN, "447.12",
    "Inductor_SMD:L_Wuerth_HCI-1890", note="no tracks underneath, only GND pour")
r("RS1", "6mR 2512 2W", "SNS_P", "VOUT_C", B, "PA2512FKF7W0R006E", OVS, "67.77", fp=R2512, sup=EK, desc="Current sense resistor 6 mOhm 1 % 2 W",
  note="Kelvin connections to U1 pins 3 and 4")
for i in range(4):
    c(f"C{9+i}", "22uF 25V", "VOUT_C", "GND", B, "GRM32ER71E226ME15L", OWN, "58.89", fp=C1210, sup=EK, desc="Ceramic 22 uF 25 V X7R 1210",
      note="alt: CL32B226KAJNFNE (own stock, 61.85 TL)" if i == 0 else "")
for i in range(2):
    add(f"C{13+i}", "100uF 35V", "Aluminium polymer 100 uF 35 V, 36 mOhm, SMD can 8x6.7 mm", {"+": "VOUT_C", "-": "GND"}, B, "A768KE107M1VLAE036", EK, OVS,
        "55.03", "Capacitor_SMD:CP_Elec_8x6.7")
r("R7", "2R2 1206", "SW", "SNUB", B, fit=False, fp="Resistor_SMD:R_1206_3216Metric", desc="Snubber resistor", note="DNP: fit only if SW ringing requires it")
c("C15", "470pF 100V C0G", "SNUB", "GND", B, fit=False, desc="Snubber capacitor 470 pF 100 V C0G 0805", note="DNP")

# ---------------------------------------------------------------- 3 controller
B = "3 LTC3895 controller"
add("U1", "LTC3895EFE", "150 V synchronous buck controller, TSSOP-38 (31 leads) with exposed pad", {
    "1 OVLO": "OVLO", "2 VPRG": "NC", "3 SENSE+": "SENSE_P", "4 SENSE-": "VOUT_C", "5 SS": "SS", "6 VFB": "VFB", "7 ITH": "ITH",
    "8 MODE": "MODE", "9 GND": "GND", "10 CPUMP_EN": "GND", "11 CLKOUT": "NC", "12 GND": "GND", "13 PLLIN": "GND", "14 PGOOD": "PGOOD",
    "15 GND": "GND", "16 NC": "NC", "17 FREQ": "FREQ", "18 DRVSET": "INTVCC", "19 DRVUV": "INTVCC", "20 TG": "TG", "21 SW": "SW",
    "22 BOOST": "BOOST", "24 BG": "BG", "26 DRVCC": "DRVCC", "28 NDRV": "DRVCC", "30 VIN": "VIN_IC", "32 EXTVCC": "EXTVCC", "34 RUN": "RUN",
    "36 PHASMD": "GND", "37 ILIM": "NC", "38 INTVCC": "INTVCC", "39 EP": "GND"}, B, "LTC3895EFE#TRPBF", EK, OWN, "1037.84",
    "ee463:LTC3895_TSSOP-38-31-1EP_4.4x9.7mm_P0.5mm_EP2.74x4.75mm_ThermalVias", note="order 2 (one spare)")
r("R8", "42k2", "FREQ", "GND", B, "RC0805FR-0742K2L", OVS, "7.06", sup=EK, note="250 kHz")
r("R9", "270k", "VIN", "RUN", B, note="UVLO 17.4 V")
r("R10", "20k", "RUN", "OVLO", B, note="13.7k if OVLO is enabled")
r("R11", "0R", "OVLO", "GND", B, "RC0805JR-070RL", OVS, "7.24", sup=EK, note="OVLO disabled; 6.19k enables OVLO at ~56 V")
c("C16", "10nF 50V", "RUN", "GND", B, "CL21B103KBANNNC", OVS, "7.24", sup=EK)
c("C17", "1uF 25V", "SS", "GND", B, "C2012X7R1E105K125AB", OVS, "16.65", sup=EK, note="soft-start 33 ms")
r("R12", "330k", "INTVCC", "SS", B, "RC0805FR-07330KL", OVS, "7.24", sup=EK, note="defeats REGSD; remove to restore it")
r("R13", "140k 0.1%", "FB_TOP", "VFB", B, "RT0805BRD07140KL", OVS, "9.05", sup=EK, desc="Resistor 140 k 0.1 % 25 ppm 0805", note="alt: ERA-6AEB1403V")
r("R14", "10k 0.1%", "VFB", "GND", B, "RT0805BRD0710KL", OVS, "8.69", sup=EK, desc="Resistor 10 k 0.1 % 25 ppm 0805", note="alt: ERA-6AEB103V")
r("R15", "10R", "VOUT", "FB_TOP", B, "RC0805FR-0710RL", OVS, "9.41", sup=EK, note="loop-gain injection resistor; Kelvin from J2")
c("C18", "DNP (22pF C0G)", "FB_TOP", "VFB", B, fit=False, note="DNP: feed-forward capacitor position")
r("R16", "10k", "ITH", "ITH_RC", B, "RC0805FR-0710KL", OVS, "7.24", sup=EK, note="Rc, design A (design B: 4.7k)")
c("C19", "4.7nF 50V", "ITH_RC", "GND", B, "CL21B472KBANNNC", OVS, "7.57", sup=EK, note="Cc, design A (design B: 22 nF)")
c("C20", "330pF 50V C0G", "ITH", "GND", B, note="Cp")
r("R17", "0R", "INTVCC", "MODE", B, "RC0805JR-070RL", OVS, "7.24", sup=EK, note="forced continuous; 100k here = pulse-skipping")
r("R18", "0R", "MODE", "GND", B, fit=False, note="DNP: Burst Mode (remove R17)")
r("R19", "100k", "INTVCC", "PGOOD", B, "RC0805FR-07100KL", OVS, "7.24", sup=EK)
r("R20", "0R", "SNS_P", "SENSE_P", B, "RC0805JR-070RL", OVS, "7.24", sup=EK, note="sense filter position (up to 100 ohm); nothing in the SENSE- line")
c("C21", "1nF 50V C0G", "SENSE_P", "VOUT_C", B, note="at U1 pins 3-4")
c("C22", "470nF 50V", "BOOST", "SW", B, "GRM21BR71H474KA88L", OVS, "16.65", sup=EK, note="within 5 mm of pins 21-22, same side, no vias")
c("C23", "10uF 25V 1206", "DRVCC", "GND", B, "GRM31CR71E106KA12L", "not in stock at e-komponent on 16 Nov -> Ozdisan", "23.89",
  fp="Capacitor_SMD:C_1206_3216Metric", desc="Ceramic 10 uF 25 V X7R 1206", note="at pin 26")
c("C24", "100nF 50V", "DRVCC", "GND", B, "CL21B104KBCNNNC", OVS, "7.24", sup=EK)
c("C25", "100nF 50V", "INTVCC", "GND", B, "CL21B104KBCNNNC", OVS, "7.24", sup=EK, note="at pin 38")
r("R21", "4R7", "VIN", "VIN_IC", B)
c("C26", "100nF 100V", "VIN_IC", "GND", B, desc="Ceramic 100 nF 100 V X7R 0805", note="at pin 30")
r("R22", "2R2", "VOUT_C", "EXTVCC", B)
c("C27", "1uF 25V", "EXTVCC", "GND", B, "C2012X7R1E105K125AB", OVS, "16.65", sup=EK, note="at pin 32")

# ---------------------------------------------------------------- 4 output and current limit loop
B = "4 Output shunt and current-limit (CC) loop"
r("RSH1", "3mR 2512 2W", "VOUT_C", "VOUT", B, "PA2512FKF7W0R003E", OVS, "72.01", fp=R2512, sup=EK, desc="Shunt 3 mOhm 1 % 2 W", note="Kelvin to U2")
add("J2", "Output 12V", TBD, {"1": "VOUT", "2": "GND"}, B, "", OZ, GEN, "",
    TB, note=TBN + "; 7.75 A in current limit, 10 A for 3 ms")
add("U2", "INA180A2", "Current-sense amplifier, gain 50, SOT-23-5", {"1 OUT": "ISENSE", "2 GND": "GND", "3 IN+": "VOUT_C", "4 IN-": "VOUT",
                                                                    "5 VS": "+5V_CC"}, B, "INA180A2IDBVR", EK, OVS, "42.00",
    "Package_TO_SOT_SMD:SOT-23-5", note="pinout A version; common mode -0.2..26 V")
c("C28", "100nF 50V", "+5V_CC", "GND", B, "CL21B104KBCNNNC", OVS, "7.24", sup=EK, note="at U2")
add("U3", "MCP6001", "Rail-to-rail op-amp, SOT-23-5", {"1 OUT": "CC_OUT", "2 VSS": "GND", "3 IN+": "VREF_CC", "4 IN-": "CC_INV", "5 VDD": "+5V_CC"},
    B, "MCP6001T-E/OT", EK, OVS, "25.34", "Package_TO_SOT_SMD:SOT-23-5", note="standard pinout (not the R or U variant)")
c("C29", "100nF 50V", "+5V_CC", "GND", B, "CL21B104KBCNNNC", OVS, "7.24", sup=EK, note="at U3")
r("R23", "20k", "ISENSE", "CC_INV", B, note="integrator R")
c("C30", "100nF 50V", "CC_INV", "CC_OUT", B, "CL21B104KBCNNNC", OVS, "7.24", sup=EK, note="integrator C (tau 2 ms)")
add("D2", "1N4148W", "Small-signal diode SOD-123, anti-windup clamp", {"A": "CC_OUT", "K": "CC_INV"}, B, "1N4148W", EK, OVS, "8.47", "Diode_SMD:D_SOD-123")
add("D1", "1N4148W", "Small-signal diode SOD-123, ITH clamp", {"A": "CC_D", "K": "CC_OUT"}, B, "1N4148W", EK, OVS, "8.47", "Diode_SMD:D_SOD-123")
r("R24", "220R", "CC_LINK", "CC_D", B, "RC0805FR-07220RL", OVS, "7.24", sup=EK)
r("R25", "0R", "ITH", "CC_LINK", B, "RC0805JR-070RL", OVS, "7.24", sup=EK, note="CC enable link: remove to disable the current-limit loop")
if CC_SUPPLY == "TL431_SHUNT":
    # 5 V rail = TL431A with two equal 0.1 % resistors: 2.495 V x 2 + IREF x 10 k = 5.01 V. The rail is also the threshold reference.
    add("U4", "TL431A", "Shunt regulator TL431A, SOT-23 (5 V rail of the current-limit circuit)", {"1 K": "+5V_CC", "2 REF": "V5_FB", "3 A": "GND"},
        B, "TL431AIDBZR", EK, OVS, "20.12", "Package_TO_SOT_SMD:SOT-23",
        note="DBZ pinout: 1 cathode, 2 ref, 3 anode; needs >= 4.7 uF on the rail (C33) for stability, see calc/t12b_cc_supply.py")
    r("R29", "820R", "DRVCC", "+5V_CC", B, note="series resistor of the shunt regulator: 6.1 mA at DRVCC 10 V, >= 1 mA left for the TL431 at 7.0 V")
    r("R26", "10k 0.1%", "+5V_CC", "V5_FB", B, "RT0805BRD0710KL", OVS, "8.69", sup=EK, desc="Resistor 10 k 0.1 % 25 ppm 0805",
      note="sets the 5 V rail together with R30 (equal values)")
    r("R30", "10k 0.1%", "V5_FB", "GND", B, "RT0805BRD0710KL", OVS, "8.69", sup=EK, desc="Resistor 10 k 0.1 % 25 ppm 0805")
    r("R27", "22k", "+5V_CC", "TRIM_HI", B, note="threshold divider top")
    add("RV1", "5k 25-turn", "Trimmer 5 k, 25 turns, 3296W", {"1": "TRIM_HI", "2": "VREF_CC", "3": "TRIM_LO"}, B, "3296W-1-502LF",
        "Ozdisan / local shop", "e-komponent lists 3296W-1-502RLF at 244.38 TL (overseas); buy locally", "",
        "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical", note="threshold 4.2-9.6 A nominal (0.22 A per turn)")
    r("R28", "3k9", "TRIM_LO", "GND", B, note="threshold divider bottom")
    c("C31", "100nF 50V", "VREF_CC", "GND", B, "CL21B104KBCNNNC", OVS, "7.24", sup=EK)
    c("C33", "10uF 25V 1206", "+5V_CC", "GND", B, "GRM31CR71E106KA12L", "not in stock at e-komponent on 16 Nov -> Ozdisan", "23.89",
      fp="Capacitor_SMD:C_1206_3216Metric", desc="Ceramic 10 uF 25 V X7R 1206", note="5 V rail; also the TL431 stability capacitor: never leave it out")
else:
    add("U4", "TL431A", "Shunt reference 2.495 V, SOT-23", {"1 K": "VREF_2V5", "2 REF": "VREF_2V5", "3 A": "GND"}, B, "TL431AIDBZR", EK, OVS, "20.12",
        "Package_TO_SOT_SMD:SOT-23", note="DBZ pinout: 1 cathode, 2 ref, 3 anode; no capacitor directly on the cathode")
    r("R26", "1k5", "+5V_CC", "VREF_2V5", B, "RC0805FR-071K5L", OVS, "7.24", sup=EK, note="1.67 mA bias")
    r("R27", "10k", "VREF_2V5", "TRIM_HI", B, "RC0805FR-0710KL", OVS, "7.24", sup=EK)
    add("RV1", "5k 25-turn", "Trimmer 5 k, 25 turns, 3296W", {"1": "TRIM_HI", "2": "VREF_CC", "3": "TRIM_LO"}, B, "3296W-1-502LF",
        "Ozdisan / local shop", "e-komponent lists 3296W-1-502RLF at 244.38 TL (overseas); buy locally", "",
        "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical", note="threshold 4.5-8.6 A")
    r("R28", "5k6", "TRIM_LO", "GND", B)
    c("C31", "100nF 50V", "VREF_CC", "GND", B, "CL21B104KBCNNNC", OVS, "7.24", sup=EK)
    add("U5", "HT7550-1", "5 V LDO, 24 V input, SOT-89", {"1 GND": "GND", "2 VIN": "LDO_IN", "3 VOUT": "+5V_CC"}, B, "HT7550-1", EK, OVS, "18.10",
        "Package_TO_SOT_SMD:SOT-89-3", note="tab = VIN; alt: LP2985A-50DBVR (SOT-23-5, different footprint)")
    r("R29", "100R", "DRVCC", "LDO_IN", B)
    c("C32", "1uF 25V", "LDO_IN", "GND", B, "C2012X7R1E105K125AB", OVS, "16.65", sup=EK)
    c("C33", "10uF 25V 1206", "+5V_CC", "GND", B, "GRM31CR71E106KA12L", "not in stock at e-komponent on 16 Nov -> Ozdisan", "23.89",
      fp="Capacitor_SMD:C_1206_3216Metric", desc="Ceramic 10 uF 25 V X7R 1206")

# ---------------------------------------------------------------- 5 test points, mechanics
B = "5 Test points and mechanics"
for i, net in enumerate(["VIN", "VIN_RTN", "GND", "GND", "GND", "VOUT", "VOUT_C", "SW", "TG_G", "BG_G", "DRVCC", "INTVCC", "EXTVCC", "ITH",
                         "PGOOD", "SS", "FB_TOP", "ISENSE", "VREF_CC", "CC_OUT", "+5V_CC"], start=1):
    add(f"TP{i}", net, "Test point, loop type", {"1": net}, B, "", "local", "generic", "", TPF)
for i in range(1, 5):
    add(f"H{i}", "M3", "Mounting hole M3, 8 mm keep-out, >= 4 mm from the edge", {}, B, "", "local", "generic", "", "MountingHole:MountingHole_3.2mm_M3")

# ================================================================= assembly groups
# All footprints stay on the board. A = basic converter (needed for the demo), B = current-limit (CC) loop, may be left
# unpopulated at the first assembly, C = reverse-polarity protection. The 3 mOhm shunt RSH1 is in group A: the output
# current and the VFB sense line pass through it.
GROUP_C = {"Q3", "D3", "R1", "C1", "R2", "R3"}
GROUP_B = {"U2", "C28", "U3", "C29", "R23", "C30", "D2", "D1", "R24", "R25", "U4", "R26", "R27", "R30", "RV1", "R28", "C31", "R29",
           "C33", "U5", "C32", "TP18", "TP19", "TP20", "TP21"}
for comp in C:
    comp["grp"] = "C" if comp["ref"] in GROUP_C else "B" if comp["ref"] in GROUP_B else "A"
GROUP_NOTE = {"R2": "group C bypass: fit R2 and R3 (0 ohm) only if Q3 is NOT fitted", "R3": "group C bypass: fit together with R2"}


def check_without(removed, refit=()):
    """Connectivity of the board when the fitted parts of the given groups are left out (refit: DNP parts fitted instead).
    Returns the nets that still carry a fitted pin but have fewer than two fitted component pins (test points do not count)."""
    left = defaultdict(list)
    for comp in C:
        on = (comp["fit"] and comp["grp"] not in removed) or comp["ref"] in refit
        if on and not comp["ref"].startswith(("TP", "H")):
            for pin, net in comp["pins"].items():
                if net != "NC":
                    left[net].append(f"{comp['ref']}.{pin.split()[0]}")
    return {net: pins for net, pins in left.items() if len(pins) < 2}


# ================================================================= KiCad pad numbers
def pads(comp, pin):
    """KiCad pad numbers behind a pin key of this file (checked against the datasheets, see kicad/footprints.md)."""
    ref = comp["ref"]
    if ref.startswith("Q"):
        return {"S": ["1", "2", "3"], "G": ["4"], "D": ["5"]}[pin]       # TDSON-8-1: pad 5 = leads 5-8 + tab
    if ref.startswith("D"):
        return {"K": ["1"], "A": ["2"]}[pin]                             # KiCad diode convention: pad 1 = cathode
    if pin in ("+", "-"):
        return ["1"] if pin == "+" else ["2"]                            # polarised capacitor: pad 1 = plus
    return [pin.split()[0]]


# ================================================================= checks
nets = defaultdict(list)
for comp in C:
    for pin, net in comp["pins"].items():
        nets[net].append((comp["ref"], pin, comp["fit"]))
errors = []
refs = [x["ref"] for x in C]
if len(refs) != len(set(refs)):
    errors.append("duplicate reference designators")
for net, pins in nets.items():
    if net == "NC":
        continue
    non_tp = [p for p in pins if not p[0].startswith("TP")]
    if len(non_tp) < 2:
        errors.append(f"net {net} has fewer than 2 component pins: {pins}")
    if not any(p[2] for p in non_tp) and net != "SNUB":      # SNUB: internal node of the DNP snubber
        errors.append(f"net {net} is connected only to unpopulated parts")
u1 = next(x for x in C if x["ref"] == "U1")
expected = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 26, 28, 30, 32, 34, 36, 37, 38, 39}
got = {int(k.split()[0]) for k in u1["pins"]}
if got != expected:
    errors.append(f"U1 pin set mismatch: missing {expected-got}, extra {got-expected}")
for must in ("VIN", "VOUT", "GND", "SW"):
    if must not in nets:
        errors.append(f"PCB-Checker net {must} missing")

# ================================================================= outputs
with open(os.path.join(HERE, "pins.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Ref", "Value", "Pin", "Net", "Fitted", "Pads"])
    for comp in C:
        for pin, net in comp["pins"].items():
            w.writerow([comp["ref"], comp["value"], pin, net, "yes" if comp["fit"] else "DNP", " ".join(pads(comp, pin))])
with open(os.path.join(HERE, "nets.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Net", "Pins"])
    for net in sorted(nets):
        w.writerow([net, " ".join(f"{r_}.{p.split()[0]}" for r_, p, _ in nets[net])])
with open(os.path.join(HERE, "netlist_by_block.md"), "w") as f:
    f.write("# Schematic connection list (generated by schematic_netlist.py)\n\n"
            "The KiCad schematic is generated from this list by kicad/make_kicad.py. Net names VIN, VOUT, GND, SW are required by PCB-Checker; add `VOUT_C` to\n"
            "`nets.output` and `VIN_RTN` handling is already in `pcb_checker.json`. DNP = footprint only.\n"
            "IC pin numbers were checked against the datasheets on 16 Nov 2026 (kicad/footprints.md).\n")
    blocks = []
    for comp in C:
        if comp["block"] not in blocks:
            blocks.append(comp["block"])
    for b in blocks:
        f.write(f"\n## {b}\n\n| Ref | Value | Connections (pin → net) | Note |\n|---|---|---|---|\n")
        for comp in [x for x in C if x["block"] == b]:
            conn = ", ".join(f"{p} → {n}" for p, n in comp["pins"].items()) or "–"
            f.write(f"| {comp['ref']}{'' if comp['fit'] else ' (DNP)'} | {comp['value']} | {conn} | {comp['note']} |\n")
    f.write("\n## Nets\n\n| Net | Pins |\n|---|---|\n")
    for net in sorted(nets):
        f.write(f"| {net} | " + ", ".join(f"{r_}.{p.split()[0]}" for r_, p, _ in nets[net]) + " |\n")
groups = {}
for comp in C:
    if comp["ref"].startswith(("TP", "H")):
        key = (comp["desc"].split(" ")[0] + " " + comp["desc"].split(" ")[1], comp["fp"])
        key = ("Test point" if comp["ref"].startswith("TP") else "Mounting hole M3", comp["mpn"], comp["fit"])
    else:
        key = (comp["value"], comp["mpn"], comp["fit"], comp["fp"], comp["grp"])
    if comp["ref"].startswith("TP"):
        key = key + (comp["grp"],)
    groups.setdefault(key, []).append(comp)
os.makedirs(os.path.join(HERE, "..", "..", "bom"), exist_ok=True)
with open(os.path.join(HERE, "..", "..", "bom", "ee463_bom.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Refs", "Qty", "Value", "Description", "MPN (example)", "Supplier", "Stock / lead time (16.11.2026)",
                "Unit price incl. VAT (TRY)", "Footprint (KiCad)", "Fitted", "Assembly group", "Notes"])
    total = 0.0
    total_grp = defaultdict(float)
    GROUP_NAME = {"A": "A basic converter", "B": "B current-limit loop (optional at first assembly)", "C": "C reverse-polarity protection"}
    for key, comps in groups.items():
        c0 = comps[0]
        notes = "; ".join(dict.fromkeys([x["note"] for x in comps if x["note"]] + [GROUP_NOTE[x["ref"]] for x in comps if x["ref"] in GROUP_NOTE]))
        value = "loop, 1.0 mm hole" if c0["ref"].startswith("TP") else c0["value"]      # test points: the value field holds the net name
        w.writerow([" ".join(x["ref"] for x in comps), len(comps), value, c0["desc"], c0["mpn"], c0["sup"], c0["stock"], c0["price"],
                    c0["fp"], "yes" if c0["fit"] else "DNP", GROUP_NAME[c0["grp"]], notes])
        if c0["price"] and c0["fit"]:
            total += float(c0["price"]) * len(comps)
            total_grp[c0["grp"]] += float(c0["price"]) * len(comps)
print(f"{len(C)} components, {len(nets)} nets, {len(groups)} BOM lines")
print(f"Priced, fitted parts (one board, no spares): {total:.0f} TRY")
print("ERRORS:" if errors else "Connectivity checks passed.")
for e in errors:
    print("  -", e)
count = {g: sum(1 for x in C if x["grp"] == g) for g in "ABC"}
print("Assembly groups: " + ", ".join(f"{g} {count[g]} parts ({sum(1 for x in C if x['grp'] == g and x['fit'])} fitted, "
                                      f"{total_grp[g]:.0f} TRY priced)" for g in "ABC"))
open_b = check_without({"B"})
print("Group B not fitted: " + ("every remaining net has at least two fitted pins (ITH: "
      + ", ".join(p for p in sorted(r_ + "." + q.split()[0] for r_, q, f_ in nets["ITH"] if not r_.startswith("TP")
                                    and next(x for x in C if x["ref"] == r_)["grp"] != "B")) + "; VFB: "
      + ", ".join(sorted(r_ + "." + q.split()[0] + ("" if f_ else " (DNP)") for r_, q, f_ in nets["VFB"])) + ")"
      if not open_b else f"OPEN NETS {open_b}"))
open_c = check_without({"C"})
open_c2 = check_without({"C"}, refit=("R2", "R3"))
print(f"Group C not fitted: open nets {open_c if open_c else 'none'}; with R2 and R3 (0 ohm) fitted instead: {open_c2 if open_c2 else 'none'}")
open_bc = check_without({"B", "C"}, refit=("R2", "R3"))
print(f"Groups B and C not fitted, R2/R3 fitted: {open_bc if open_bc else 'no open nets'}")
