# TPS54360B 5 V bucks, TPS25200 eFuse, pulse-rated precharge (2026-10-24)

Board `abx-motion-brushless`. Nothing committed. KiCad was closed for every write.
Backups of every touched file: `.claude/handoff/bak/pre_tps54360/` (Power, Bus_Breaker, root sheet, board, .kicad_pro, abx-symbols, handoff, `bl/` scripts).

## Result
| check | before | after |
|---|---|---|
| ERC errors | 0 | 0 |
| ERC warnings | lib_symbol_mismatch 14, pin_to_pin 2, multiple_net_names 1 | unchanged (same 17) |
| DRC parity | 0 | 0 |
| clearance / short / courtyard / hole | 0 | 0 |
| starved_thermal | 9 | 9 (same pads) |
| lib_footprint_mismatch | 36 | 35 (the old HSOP U1 is gone) |
| silk (over copper / overlap / edge) | 199 / 199 / 3 | unchanged |
| track_dangling | 0 | 0 |
| unconnected | 224 | 262 (all on the new or staged parts; see PCB) |

- Parts: 343 -> 357.
- Locked groups unchanged: critical_routes 424, PWR_VIAS 535.
- cleanup_routes 643 -> 630: the 13 removed tracks are the dead +BATT stub to the old U1.

## 1. Both 5 V bucks are now TPS54360BDDAR (one BOM)
U1 (board +5V) and U901 (+5V_AUX) use the same parts and values. The design follows SNVSB93 section 8.2.2 (equation numbers below are from it).

**Inputs.**
- VIN is 25-42 V, with transients up to 50 V. The device is rated 60 V operating, 65 V abs max.
- Vout is 5.0 V; U901 runs 2 A continuous.

**Loads on U1 (+5V).**
- AP2112 U2 (+3V3) and U705 (+3V3_ESC).
- Hall/encoder connectors J304/J404, J703.
- CAN U704, LM339 U802, LEDs.
- Total is below about 1.5 A worst case, against the 3.5 A device rating.

| item | value | why |
|---|---|---|
| fsw | RT 196k -> 494 kHz (eq. 8) | Far above the 20-30 kHz ESC PWM; 94 kHz away from U511 (400 kHz). At 50 V: eq. 9 (pulse skip) 842 kHz, eq. 10 (foldback) 1.3 MHz. On-time 224 ns at 50 V, against t_on(min) 135 ns. |
| Vout | RHS 53.6k / RLS 10.2k -> 5.004 V (eq. 3) | U1: R4/R5; U901: R901/R902. |
| L | 10 uH Sunlord MWSA0603S-100MT (Isat 5.5 A, Irms 4.5 A, 67 mOhm) | Eq. 28 with KIND 0.3 at 3 A gives 9.9 uH (42 V) to 10.1 uH (50 V). Ripple 0.81-0.91 A (25-50 V). Ipk 2.45 A at 2 A, 3.45 A at 3 A. Isat >= 4.5 A as asked. |
| catch diode | PDS5100-13, 100 V 5 A, PowerDI-5 | 100 V leaves margin over 50 V plus ringing (60 V minimum asked). Eq. 37 at 2 A: 1.23 W (42 V), 1.31 W (50 V). It needs a copper pad. |
| Cout | 2x 47 uF/10 V X5R 1206 (~45 uF effective at 5 V) | Eq. 32 (1.5 A step, 5 %) needs 24 uF. Eq. 33 (2.5 -> 1 A, 5 % overshoot) needs 20 uF. Eq. 34 (25 mV ripple) needs 10 uF. U1: C7/C8; U901: C906/C907. |
| Cin | 2x 4.7 uF/100 V X7R 1206 + 100 nF/100 V | About 3.5 uF effective at 42 V (>= 3 uF asked). Eq. 38: 1.0 A rms (25 V, 2.5 A). Eq. 39: 0.36 V ripple. Same parts as before (C2-C4, C901-C903), so the placed footprints are kept. |
| BOOT | 100 nF X7R 0603 | C6 / C905. |
| compensation | Rc 9.1k, Cz 10 nF, Chf 68 pF C0G | fp = 1.77 kHz (2.5 A, 45 uF); fz(ESR) = 1.4 MHz. fco = min(eq. 46, eq. 47) = 20.9 kHz. Eq. 48 gives 8.8k, so 9.1k. Eq. 49: 9.9 nF. Eq. 51: 71 pF (eq. 50: 12 pF). U1: R11/C11/C12; U901: R904/C904/C911. |
| soft start | internal, 1024 cycles = 2.1 ms (eq. 6) | The TPS54360B has no SS pin. |
| EN/UVLO | 560k (0805) / 33k | See below. U1: R12/R13; U901: R907/R908. |
| U1/U901 losses (2 A) | IC 0.53 W (42 V), 0.68 W (50 V); inductor 0.27 W | About a 25 C rise in DDA. Efficiency about 83 % at 42 V. |

**EN/UVLO thresholds** (eq. 4/5; EN 1.1-1.3 V, I1 0.58-1.8 uA, Ihys 2.2-4.5 uA).

| | typical | tolerance |
|---|---|---|
| start | 20.9 V | 18.8-23.0 V |
| stop | 19.0 V | 16.2-21.8 V |

- How this fits the rest of the board:
  - The logic is always up before the bus breaker can close (30.7 V, minimum 30.2 V).
  - The logic stays up below the LM339 UV gate (26.8 V) and the TPS48111 OFF point (28.9 V).
  - The 10S pack minimum is 25 V.
  - The old LMR36520 had EN tied to +BATT (no UVLO).
- EN at 50 V is 2.9 V, against an abs max of 8.4 V, so no zener is needed.

## 2. +5V_AUX eFuse: MIC2009 -> TPS25200DRVR (U902)
- **The MIC2009 cannot do it.** Its adjustable range ends at 2.0 A. CLF is only specified up to 2 A (210/250/286 V), so a 2.2 A minimum would need RSET <= 95 R, which gives 2.6 A typ / 3.0 A max, outside the datasheet.
- **TPS25200** (TI, SLVSCJ0F): 2.5-6.5 V (20 V abs max), 60 mOhm, 2.6 A continuous, 5.4 V OUT clamp, 7.6 V OVLO, open-drain FAULT, WSON-6 2x2.
- **Eq. 1, RILIM = R905 39k:**
  - IOS(nom) = 98322 / 39^1.003 = **2.49 A**
  - IOS(min) = 97399 / 39^1.015 - 30 mA = **2.33 A** (>= 2.2 A: a 2 A load never trips)
  - IOS(max) = 96754 / 39^0.985 + 30 mA = **2.65 A**
  - The datasheet table agrees: 40.2k -> 2.27 / 2.42 / 2.57 A.
- **Heat at 2 A:** 0.40 W at 99 mOhm hot, x 66.5 C/W = 27 C.
- **Connections:**
  - EN tied to IN (5V_AUX_BUCK, 5 V < 7 V abs max).
  - FAULT -> AUX5_FLT_N (R906 10k to +3V3) -> PD11, unchanged.
  - C909 1 uF in, C910 10 uF out, D901 / J511 unchanged.
- New abx symbol `abx:TPS25200DRV` (added by aux5v.py). Footprint `Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm_ThermalVias` (pad 7 = PowerPAD = GND).
- At 2 A, +5V_AUX is about 5.0 V - 0.2 V (eFuse) = 4.8 V at J511.

## 3. Precharge resistors R803/R804: changed (they would not survive)
**Pulse into a shorted bus.** One timeout: R827 220k x C809 2.2 uF x ln(3.3/2.27) = 0.181 s, up to about 0.20 s with C809 at +10 %.

**Old (2x 10 R generic 2512):**
- 42 V / 20 R = 2.1 A, 88.2 W total.
- **44.1 W and 7.9 J per resistor.**

**Allowed per 2512 resistor at 0.2 s:**
- Vishay CRCW2512 (standard thick film), single-pulse curve: about 3 W.
- Yageo SR2512 (anti-surge, J tol), single-pulse curve: about 30 W (44 W at 0.1 s, 13 W at 1 s, log interpolation).
- TO-263 power thick film (TPAL0263, 35 W): its pulse curve is flat at 35 W above 10 ms, so 6.3 J at 0.18 s.

All three are short of 44 W.

**New: 4x Yageo SR2512JK-077R5L (7.5 R, anti-surge 2512) in series = 30 R.**
- Order: R803 (BUS_SNS-PRE_M), R830 (PRE_M-PRE_M2), R831 (PRE_M2-PRE_M3), R804 (PRE_M3-PRE_D).
- **Short:** 42 V / 30 R = 1.4 A, 58.8 W total, **14.7 W and 2.6-2.9 J per resistor**, against about 30 W allowed: **2x margin**.
- **Normal precharge:**
  - tau = 30 R x about 1.1 mF (4x 220 uF + 14x 10 uF derated) = 33 ms.
  - 92 % is reached after 2.53 tau = 83 ms, plus about 36 ms of BST charge = about 120 ms.
  - The timeout minimum is about 0.16 s, so precharge still finishes in time.
- **Energy per normal start:** 1/2 C V^2 = 0.97 J in total.
- **Fallback if stock runs short:** 3x SR2512JK-0710RL (10 R, C876857, 4.1k in stock) = 30 R. That is 19.6 W each, a 1.5x margin.
- R803/R804 keep their pads (re-valued). R830/R831 are new and staged off-board.

## Parts and LCSC (JLC local DB, 2026-10-24)
| ref(s) | part | LCSC | stock / type |
|---|---|---|---|
| U1, U901 | TPS54360BDDAR (SO-8 PowerPAD DDA) | C524806 | 58.9k ext |
| D3, D902 | PDS5100-13 (100 V 5 A PowerDI-5) | C124201 | 29.7k ext |
| L1, L901 | Sunlord MWSA0603S-100MT 10 uH | C132141 | 34.2k ext |
| C7, C8, C906, C907 | 47 uF 10 V X5R 1206 CL31A476MPHNNNE | C96123 | 363k **basic** |
| C2, C3, C901, C902 | 4.7 uF 100 V X7R 1206 HHV1206R7475K101NSPJ | C22367839 | 487k ext |
| C4, C903 | 100 nF 100 V X7R 0603 | C88219 | 2.1M ext |
| C6, C905 | 100 nF 50 V X7R 0603 | C14663 | basic |
| C11, C904 | 10 nF 50 V X7R 0603 | C57112 | basic |
| C12, C911 | 68 pF C0G 0603 | C28262 | 117k preferred |
| R10, R903 | 196k 1 % 0603 | C22930 | 58k ext |
| R11, R904 | 9.1k 1 % 0603 | C23260 | basic |
| R4, R901 | 53.6k 1 % 0603 | C23074 | 76k ext |
| R5, R902 | 10.2k 1 % 0603 | C22772 | 66k ext |
| R12, R907 | 560k 1 % 0805 | C15785 | 60k ext |
| R13, R908 | 33k 1 % 0603 | C4216 | basic |
| U902 | TPS25200DRVR | C128401 | 20.7k ext |
| R905 | 39k 1 % 0603 | C23153 | basic |
| R803, R804, R830, R831 | Yageo SR2512JK-077R5L 7.5 R | C876902 | **863 only** ext |

- LMR36520FADDA, SRP7028A-150M and MIC2009 are no longer used.
- C5 (the LMR VCC cap) is deleted.

## Files
- **Schematic**
  - `Power.kicad_sch` (regenerated by `bl/aux5v.py`):
    - The hand-drawn LMR36520 U1, C5 and L1 (with their stubs, labels and power symbols) are removed.
    - The new U1 + L1 + D3 + R10-R13 + C11/C12 block is injected at x 375-510, y 35-115. A note sits at the old U1 spot.
    - The hand-drawn R4/R5/C2-C4/C6-C8 are re-valued.
    - The U901 block is regenerated.
    - Unused cached lib symbols are dropped.
  - `Bus_Breaker.kicad_sch` (`bl/breaker.py`).
  - `abx-symbols.kicad_sym` (+abx:TPS25200DRV).
  - `.kicad_pro`: `/Power_Supply/U1_SW` added to Power_LV.
- **PCB**
  - `bl/f8.py`:
    - added U1, L1, D3, R10-R13, C11, C12, D902, R903, R904, R907, R908, C911, R830, R831 (staged at x 355-380);
    - replaced U901/L901/U902 in place (already off-board);
    - removed old U1, L1, C5.
  - Then new `bl/tpsclean.py`:
    - deleted the U1_SW/BOOT/FB/VCC(->COMP) tracks (46 in total, with PRE_M);
    - deleted the PRE_M copper (it would short R804 pad 1, now PRE_M3);
    - deleted the dead +BATT stub from C4 to the old U1 pins (10 segments, cleanup_routes);
    - deleted the zones PWR_GND_EP_U1_F/_B.
- **Scripts**
  - `bl/aux5v.py` is rewritten: it reproduces the whole change. It includes a one-time migration that strips the old LMR/MIC2009 injection.
  - `bl/breaker.py`: 4-resistor precharge string and texts.
  - `bl/pours.py`: skips the U1 EP zones while U1 is off-board. Tested on a copy: same DRC, 64 zones, groups unchanged.
  - `buckplace.py` / `critical.py` do not reference U1/U901 (unchanged). `aux.py` needed no change.
- **Not touched:** the U511 24 V block.

## Open / owner
1. **Place and route the new U1 block** (U1 DDA, D3, L1, R10-R13, C11/C12) where the old U1 was (x 66-84, y 106-122).
   - Keep the hot loop small: C2/C4 -> pin 2 -> SW pin 8 -> D3 K -> D3 A -> Cin GND.
   - Use buckplace.py's U511 pattern. Then add U1 to pours.py's SW/EP zones (the EP zones are rebuilt automatically once U1 is on the board).
2. Place and route the staged U901/U902 block, R830/R831 next to R803/R804, and the rest of the 55 + 17 staged parts.
3. **SR2512JK-077R5L stock is only 863** (4 per board). For a large run, use the 3x 10 R fallback above or second-source an anti-surge 2512 (Vishay CRCW-HP, KOA SG73P) and check its single-pulse curve at 0.2 s.
4. **D2 SMCJ43A (+BATT TVS) clamps at up to about 69 V at full Ipp.** That is above the TPS54360B abs max of 65 V (the LMR36520 had the same limit). Consider SMCJ40A, or accept it, since the transients are about 50 V.
5. **USB on the bench without the pack.** +5V back-feeds +BATT through L1 and the U1 high-side body diode (also true with the LMR). UVLO keeps the buck off; the +BATT loads see about 4.3 V.
6. **Thermals at 2 A on +5V_AUX.** D902 1.3 W needs copper (PowerDI-5 tab); U901 0.55-0.7 W; U902 0.4 W.
