# Aux rails + brake driver: component values (24 V/5 A, 12 V/3 A, DRV8876)

> AS BUILT (bl/aux.py): DRV8874PWPR instead of DRV8876 (0.2 vs 0.7 Ohm), AIPROPI 450 uA/A -> R532 = 2.2k for 3.0 A; catch diodes PDS5100H-13 (PowerDI-5); blocking SS54 D523 between J512 and VM_BRK.
Sources: TPS54560B SLVSF00, TPS54360B SNVSB93 (both use the same equation numbers, design section 8.2.2), DRV8876 SLVSDS7B.
Nets: +BATT, GND, 3V3, +24V, +12V, SW_A/SW_B, VM_BRK. LCSC numbers: only C14663 (100 nF 50 V X7R 0603) and C25804 (10 k 1 % 0603) are ones I am sure of; check every other part on LCSC before ordering.

## Block A: +24 V / 5 A, U511 TPS54560BDDAR, fsw 400 kHz
| Ref | Value | Rating | Footprint | Connects |
|---|---|---|---|---|
| U511 | TPS54560BDDAR | 60 V op / 65 V abs | Package_SO:TI_SO-PowerPAD-8_ThermalVias (DDA0008B; pad 9 = EP) | 1 BOOT, 2 +BATT, 3 EN_A, 4 RT_A, 5 FB_A, 6 COMP_A, 7+9 GND, 8 SW_A |
| C520-C523 | 2.2 uF X7R ×4 | 100 V | Capacitor_SMD:C_1210_3225Metric | +BATT / GND (at pins 2/7) |
| C524 | 100 nF X7R | 100 V | Capacitor_SMD:C_0603_1608Metric | +BATT / GND (closest to pin 2) |
| C525 | 47 uF Al-elec, low ESR (shared with B) | 80 V (>=63 V) | Capacitor_SMD:CP_Elec_10x10.5 | +BATT / GND |
| R520 | 590 k 1 % (RUVLO1) | 0805 for 54 V | Resistor_SMD:R_0805_2012Metric | +BATT / EN_A |
| R521 | 26.7 k 1 % (RUVLO2) | | Resistor_SMD:R_0603_1608Metric | EN_A / GND |
| R522 | 243 k 1 % (RT) | | Resistor_SMD:R_0603_1608Metric | RT_A / GND |
| R523 | 348 k 1 % (RHS) | | Resistor_SMD:R_0603_1608Metric | +24V / FB_A |
| R524 | 12.0 k 1 % (RLS) | | Resistor_SMD:R_0603_1608Metric | FB_A / GND |
| R525 | 14.3 k 1 % (R4) | | Resistor_SMD:R_0603_1608Metric | COMP_A / CZ_A |
| C526 | 6.8 nF X7R (C5) | 50 V | Capacitor_SMD:C_0603_1608Metric | CZ_A / GND |
| C527 | 56 pF C0G (C8) | 50 V | Capacitor_SMD:C_0603_1608Metric | COMP_A / GND |
| C528 | 100 nF X7R (BOOT), C14663 | 50 V | Capacitor_SMD:C_0603_1608Metric | BOOT_A / SW_A |
| L520 | 22 uH, Isat >= 9.5 A (>= 8 A min), Irms >= 6.5 A, DCR <= 35 mOhm: Sunlord MWSA1265S-220MT (check the specs) | | Inductor_SMD:L_Sunlord_MWSA1265S | SW_A / +24V |
| D520 | Vishay V10P10-M3/86A Schottky (alt: SS10P10) | 100 V, 10 A | Package_TO_SOT_SMD:TO-277A (pad 3 tab = K, pads 1+2 = A) | K: SW_A, A: GND |
| C529-C533 | 10 uF X7R ×5 | 50 V | Capacitor_SMD:C_1210_3225Metric | +24V / GND |

Key calcs (A):
- fsw: Eq 9 at 54 V gives 3.4 MHz (pulse-skip limit); Eq 10 (short-circuit foldback, ICL 9.5 A max) gives 1.09 MHz. The real limit is the high duty at 28 V: D = 0.886, which at 400 kHz leaves t_off = 286 ns (t_on(min) = 135 ns is not a factor). 400 kHz also keeps the diode and switching losses low at 42-54 V. Eq 7: RT = 242.5 k, so 243 k (Eq 8: 399.6 kHz).
- Dropout: Eq 1 with Rds(on) 190 mOhm max and Vf 0.6 V gives VIN(min) = 25.4 V, so there is 2.6 V of headroom at the 28 V sag. Eq 2 (monotonic start at full load): Vout(max) = 24.6 V at 28 V in but only 23.7 V at 27 V, so keep the 5 A load off until the rail is up (or start it while VIN >= 28 V).
- L (Eq 28, KIND 0.3): 17.1 uH at 42 V, 22.2 uH at 54 V, so 22 uH. Ripple (Eq 29): 0.39 A at 28 V, 1.17 A at 42 V, 1.52 A at 54 V (all above the 150 mA minimum). Ipk = 5.76 A (Eq 31).
- Cout: Eq 32 (2.5 A step, 3 %) needs 17.4 uF; Eq 33 needs 7.8 uF; Eq 34 (0.5 % ripple) needs 3.9 uF. A 10 uF/50 V 1210 keeps only about 4.5 uF at 24 V, so 5 caps give about 22.5 uF effective. Ripple current (Eq 36) is 0.44 A.
- Cin: Eq 38 gives 2.5 A rms worst case (VIN 42-54 V). Four 2.2 uF/100 V give about 5 uF effective (TI asks for >= 3 uF). Eq 39 ripple: 0.63 V peak-to-peak, which the bulk C525 reduces.
- FB (Eq 3, Vref 0.8 V +/-1 %): 0.8 × (1 + 348/12.0) = 24.00 V.
- Compensation (Eq 44-51, gmps 17 A/V, gmea 350 uS): fp = 1.47 kHz, fz(ESR) about 12 MHz, Eq 46 = 132 kHz, Eq 47 = 17 kHz. I picked fco = 20 kHz (fsw/20). R4 = 14.26 k, so 14.3 k. C5 = 7.55 nF, so 6.8 nF (zero at 1.64 kHz). C8: Eq 51 gives 55.6 pF (Eq 50 gives 0.9 pF), so 56 pF.
- UVLO (Eq 4/5, Ihys 3.4 uA, I1 1.2 uA, Ven 1.2 V): R1 = 588 k, so 590 k; R2 = 26.6 k, so 26.7 k. Typical start/stop is 27.0/25.0 V; across tolerances it spreads 25.1-29.0 V (start) and 23.8-26.3 V (stop). EN at 54 V is 2.5 V, under the 8.4 V abs max, so no zener is needed. Use the divider rather than a plain pull-up: with a pull-up the part starts at 4.3 V and sits in dropout on an empty pack.
- Losses at 36 V in, 5 A out (Eq 52-56, Eq 37; Rds 92 mOhm at 25 C / 130 mOhm hot):
  - IC: conduction 1.53/2.17 W, switching 0.63 W (trise 8.8 ns), gate drive 0.04 W, so 2.2-2.85 W.
  - Diode: 1.08 W (Vf 0.6 V, Cj 300 pF). Inductor: about 0.95 W.
  - Efficiency: 96.1-96.6 %.

## Block B: +12 V / 3 A, U512 TPS54360BDDAR, fsw 500 kHz
| Ref | Value | Rating | Footprint | Connects |
|---|---|---|---|---|
| U512 | TPS54360BDDAR (same pinout as the non-B TPS54360DDA) | 60 V / 65 V abs | Package_SO:TI_SO-PowerPAD-8_ThermalVias | 1 BOOT, 2 +BATT, 3 EN_B, 4 RT_B, 5 FB_B, 6 COMP_B, 7+9 GND, 8 SW_B |
| C534-C536 | 2.2 uF X7R ×3 | 100 V | Capacitor_SMD:C_1210_3225Metric | +BATT / GND |
| C537 | 100 nF X7R | 100 V | Capacitor_SMD:C_0603_1608Metric | +BATT / GND (at pin 2) |
| R526 | 590 k 1 % | 0805 | Resistor_SMD:R_0805_2012Metric | +BATT / EN_B |
| R527 | 26.7 k 1 % | | Resistor_SMD:R_0603_1608Metric | EN_B / GND |
| R528 | 196 k 1 % (RT) | | Resistor_SMD:R_0603_1608Metric | RT_B / GND |
| R529 | 140 k 1 % (RHS) | | Resistor_SMD:R_0603_1608Metric | +12V / FB_B |
| R530 | 10.0 k 1 % (RLS), C25804 | | Resistor_SMD:R_0603_1608Metric | FB_B / GND |
| R531 | 9.53 k 1 % (R4) | | Resistor_SMD:R_0603_1608Metric | COMP_B / CZ_B |
| C538 | 8.2 nF X7R (C5) | 50 V | Capacitor_SMD:C_0603_1608Metric | CZ_B / GND |
| C539 | 68 pF C0G (C8) | 50 V | Capacitor_SMD:C_0603_1608Metric | COMP_B / GND |
| C540 | 100 nF X7R (BOOT), C14663 | 50 V | Capacitor_SMD:C_0603_1608Metric | BOOT_B / SW_B |
| L521 | 22 uH, Isat >= 6.8 A (>= 5.5 A min), Irms >= 4 A, DCR <= 45 mOhm: Sunlord MWSA1005S-220MT (check the specs) | | Inductor_SMD:L_Sunlord_MWSA1005S | SW_B / +12V |
| D521 | V10P10-M3/86A (same part as D520, one BOM line; alt PDS5100H-13 in Diode_SMD:D_PowerDI-5, pad 1 = K) | 100 V | Package_TO_SOT_SMD:TO-277A | K: SW_B, A: GND |
| C541-C543 | 10 uF X7R ×3 | 50 V | Capacitor_SMD:C_1210_3225Metric | +12V / GND |

Key calcs (B):
- fsw: Eq 9 gives 1.73 MHz and Eq 10 gives 1.01 MHz at 54 V (ICL 6.8 A max). At 500 kHz the on-time at 54 V is 468 ns, well above the 135 ns minimum. Eq 7: RT = 193.6 k, so 196 k (Eq 8: 494 kHz). Running 400/494 kHz keeps the two bucks off a common frequency.
- L (Eq 28): 19.0 uH at 42 V, 20.7 uH at 54 V, so 22 uH. Ripple 0.62-0.85 A, Ipk 3.42 A.
- Cout: Eq 32 (1.5 A step, 3 %) needs 16.7 uF, Eq 33 needs 11.3 uF, Eq 34 needs 3.5 uF. A 10 uF/50 V keeps about 6.5 uF at 12 V, so 3 caps give about 19.5 uF.
- Cin: Eq 38 gives 1.48 A rms at 28 V; Eq 39 gives 0.42 V ripple with about 3.6 uF effective.
- FB: 0.8 × (1 + 140/10.0) = 12.00 V. Eq 1: VIN(min) = 12.8 V, which is never a concern.
- Compensation (gmps 12 A/V): fp = 2.04 kHz, Eq 47 = 22.6 kHz (the TPS54360B datasheet says take the lower of Eq 46/47), so fco = 22 kHz. R4 = 9.63 k, so 9.53 k. C5 = 8.18 nF, so 8.2 nF. C8 = 66.8 pF, so 68 pF.
- UVLO: same divider and thresholds as Block A (27/25 V). Keep the two dividers separate: each EN pin sources its own hysteresis current.
- Losses at 36 V, 3 A: IC 0.81-0.92 W (conduction 0.28-0.39 W, switching 0.47 W). The diode dominates at 1.2 W (it conducts 65 % of the period). Inductor about 0.48 W. Efficiency about 93.3 %.

## Block C: DRV8876PWPR brake driver, U513 (HTSSOP-16 PWP)
Pin table (PWP):
- 1 EN/IN1: control input, 100 k internal pulldown
- 2 PH/IN2: control input, 100 k internal pulldown
- 3 nSLEEP: high = active, low = sleep; 100 k internal pulldown
- 4 nFAULT: open-drain fault output
- 5 VREF: current-limit reference input (0-3.6 V)
- 6 IPROPI: current-proportional output, 1000 uA/A
- 7 IMODE: quad-level current-mode select
- 8 OUT1
- 9 PGND
- 10 OUT2
- 11 VM: 4.5-37 V supply
- 12 VCP: charge-pump output, 100 nF to VM
- 13 CPH and 14 CPL: 22 nF flying capacitor between them
- 15 GND
- 16 PMODE: tri-level mode select
- 17 thermal pad (EP): to GND

| Ref | Value | Rating | Footprint | Connects |
|---|---|---|---|---|
| U513 | DRV8876PWPR | VM 37 V op / 40 V abs | Package_SO:HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask3x3mm_ThermalVias (pad 17 = EP) | as pin table |
| C544 | 100 nF X7R (CVM1), C14663 | 50 V | Capacitor_SMD:C_0603_1608Metric | VM_BRK / GND (at pin 11) |
| C545 | 10 uF X7R | 50 V | Capacitor_SMD:C_1210_3225Metric | VM_BRK / GND |
| C546 | 100 uF Al-elec (CVM2 bulk) | 50 V | Capacitor_SMD:CP_Elec_8x10.5 | VM_BRK / GND |
| C547 | 100 nF X7R (CVCP), C14663 | 50 V (>= 16 V needed) | Capacitor_SMD:C_0603_1608Metric | VCP / VM_BRK |
| C548 | 22 nF X7R (CFLY) | 50 V (VM-rated) | Capacitor_SMD:C_0603_1608Metric | CPH / CPL |
| C549 | 10 nF X7R, DNP by default (IPROPI filter) | 50 V | Capacitor_SMD:C_0603_1608Metric | IPROPI / GND |
| R532 | 1.00 k 1 % (RIPROPI) | | Resistor_SMD:R_0603_1608Metric | IPROPI (and MCU ADC) / GND |
| R533 | 10.0 k 1 % (VREF top), C25804 | | Resistor_SMD:R_0603_1608Metric | 3V3 / VREF |
| R534 | 100 k 1 % (VREF bottom) | | Resistor_SMD:R_0603_1608Metric | VREF / GND |
| R535 | 10 k (nFAULT pull-up), C25804 | | Resistor_SMD:R_0603_1608Metric | 3V3 / nFAULT |
| R536 | 0 Ohm (IMODE: fitted = GND = level 1; DNP = Hi-Z = level 4) | | Resistor_SMD:R_0603_1608Metric | IMODE / GND |
| R537 | 0 Ohm (PMODE high = PWM mode) | | Resistor_SMD:R_0603_1608Metric | PMODE / 3V3 |
| D522 | SMBJ28A TVS | 28 V standoff, VBR 31.1-34.4 V | Diode_SMD:D_SMB | K: VM_BRK, A: GND |
| JP (header) | VM select 24 V / 12 V, 2.54 mm shunt rated >= 3 A | | Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical | +24V / VM_BRK / +12V |

Behaviour and calcs (C):
- PWM mode: PMODE high, latched when nSLEEP goes high (Table 2).
- IN1/IN2 truth table (Table 4):
  - 00 = coast: both outputs Hi-Z.
  - 01 = reverse: OUT1 low, OUT2 high.
  - 10 = forward: OUT1 high, OUT2 low.
  - 11 = brake: both low-side FETs on (slow decay).
  - nSLEEP = 0 puts both outputs in Hi-Z.
- Sleep timing: tSLEEP <= 1 ms to enter sleep, tWAKE <= 1 ms to wake. The internal pulldowns keep the outputs off while the MCU is in reset, so a spring brake stays applied (fail-safe).
- IMODE: level 1 (pin at GND): fixed off-time, tOFF 25 us, auto-retry after tRETRY 2 ms, and nFAULT reports only overcurrent. This is the only mode that regulates current at 100 % duty (section 7.3.3.2.1), which the long on-time loads need. Cycle-by-cycle needs a new input edge to re-enable the outputs, so it does not fit. Latch-off (Hi-Z) is the option if the MCU will clear faults by toggling nSLEEP.
- ITRIP (Eq 3, 4, 6): RIPROPI = 1.00 k and VREF = 3.3 × 100/110 = 3.00 V give ITRIP = 3.0 A, with VIPROPI = 3.0 V at 3 A (ADC-safe; the clamp tracks VREF).
  - Simpler option: tie VREF straight to 3V3 and use RIPROPI = 1.10 k.
  - For 2 A, use RIPROPI = 1.50 k.
  - At 3 A, IPROPI sources 3 mA, which is the recommended maximum.
- Thermal (Eq 17, Rds 0.35+0.35 Ohm × 1.25 hot; RθJA about 32 C/W on 4L 2 oz):
  - 2 × 0.6 A coils (1.2 A): 1.26 W, about a 40 C rise. Fine.
  - 3 A: 7.9 W. Not sustainable; the part hits TSD.
  - About 1.5 A is the continuous limit. The 3 A ITRIP is a stall limit only: the MCU must stop the drive within about 0.1-0.3 s using IPROPI.
- Coil decay when nSLEEP drops (or on UVLO): current returns through the body diodes into VM. Energy into VM for two coils:
  - L 0.1 H: 15 mJ. L 0.3 H at 0.5 A: 44 mJ. L 0.3 H at 0.6 A: 63 mJ.
  - With only about 122 uF on the rail, 63 mJ pumps it to about 40 V, the abs max.
  - The bucks are non-synchronous and cannot sink this current. Hence C546 (100 uF) and the SMBJ28A, which clamps at about 34-36 V at 1-2 A.
  - Gentler option: command 11 (brake) first and let the current decay in the coil resistance, then drop nSLEEP. This puts no energy into VM but engages the brake more slowly (tau = L/R).

## Warnings
1. U511 thermal: 2.2-2.85 W at 5 A. With RθJA about 30 C/W (2 oz, many vias, large GND pour on L1-L4) that is a 65-85 C rise. Rate the 24 V rail 4 A continuous (IC 1.9 W) and 5 A peak, or check against the SOA curves (Fig 33-36).
2. TPS54560B: the internal BOOT-refresh low-side FET "is disabled at 24-V output and re-enabled at 21.5 V" (section 7.3.4). With VIN >= 28 V the part never enters dropout and the catch diode refreshes BOOT every cycle. Do not expect 100 % duty operation from this rail.
3. The DRV bulk C546 sits on +24V when the jumper selects 24 V. It lowers the loop crossover (stable direction). Measure a Bode plot or a load step with it fitted.
4. With 2 × 3 A stall loads in parallel (option b), the 3.5 A device rating (IOCP min 3.5 A) caps the pair at about 1.5 A each. For real 3 A stall loads use the pin-compatible DRV8874PWPR (200 mOhm total). Its AIPROPI is different (about 450 uA/A, from memory), so recompute R532.
5. If a brake coil has a built-in suppressor diode, never drive it in reverse (01): that forward-biases the diode, trips OCP, and releases very slowly.
6. A VM rail transient above 37 V is outside the recommended range (40 V abs max), so D522 must be fitted whenever inductive brake coils are connected. The other +24V loads also see the clamp voltage.
7. Inductor and diode LCSC part numbers and their Isat/Vf/Cj are from memory: check them before ordering.
