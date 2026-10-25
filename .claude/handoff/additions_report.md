# Owner-approved additions (2026-10-24)

Board `abx-motion-brushless`, branch `v1.0-bl-wip`. Nothing committed. KiCad was closed for every write.
Backups of every touched file: `.claude/handoff/bak/pre_additions/` (sheets, root, abx-symbols, board, .kicad_pro, handoff, `bl/` scripts).

## Result
| check | before | after |
|---|---|---|
| ERC errors | 0 | 0 |
| ERC warnings | lib_symbol_mismatch 10, multiple_net_names 1 (VBAT_IN/V_RAW_IN, old), isolated_pin_label 2 (BUS_EN, PRECHG_EN) | lib_symbol_mismatch 14 (+Q804, U708-U710: the same KiCad-library quirk as Q8xx/U201), multiple_net_names 1, pin_to_pin 2 (U711 SA0 and SDX tied to GND: intended) |
| DRC parity | 0 | 0 |
| clearance / short / courtyard / hole | 0 | 0 |
| starved_thermal | 9 | 9 (same pads) |
| lib_footprint_mismatch / silk | 36 / 199+199+3 | unchanged |
| unconnected | 82 | 224: the +142 are all on the 55 new staged parts; no old net got worse |

Parts 288 -> 343 (55 new, R807 and R806 re-valued). Copper, zones (66) and the locked groups are unchanged: critical_routes 424, PWR_VIAS 535, cleanup_routes 643, 3890 tracks.
New footprints are staged off-board at x 240-340, y 60-200 (right of R711/R712), not placed or routed.

## 1. BRK_FLT_N -> STM32 PD9
- U701 pin 56 (PD9) = BRK_FLT_N (global), input. R510 10k pull-up to +3V3 kept (PD9 is 5 V tolerant anyway).
- The Brakes sheet note was edited in place (TODO removed); `bl/aux.py` carries the same text.

## 2. Hardware-autonomous bus breaker (Bus_Breaker, U801 TPS48111)
**The TPS48111 has no built-in precharge -> main sequencing** (SLUSEE5E 8.3.2.2: INP and INP_G are independent CMOS inputs; the MCU-free app note does not exist).
- TMR is only the overcurrent fault timer (8.3.3).
- So the sequence is made by a small comparator block running from the always-on logic rails (+5V/+3V3 come from +BATT, before the breaker).
- The Bus_Breaker sheet had no E-stop function; the E-stop stays on the DRV enables / brake nSLEEP.
- TODO note removed; header notes rewritten (no ESP32 mentions).

**UVLO (EN/UVLO, 1.18 V rising / 1.11 V falling, fixed hysteresis).**
- R806 300k / R807 12k = /26 (was 470k / 20.5k = 28 V).
- ON 1.18 x 26 = **30.7 V** (3.07 V/cell; tolerance 30.2-31.2 V).
- OFF 1.11 x 26 = **28.9 V** (2.89 V/cell; tolerance 28.6-29.4 V).
- Divider current 135 uA at 42 V; EN leakage error < 1 mV. C802 100 nF kept.
- Basic-part values; R806/R807 keep their pads, so the routed copper stays (a 3-resistor version shorted an existing track and was dropped).

**Sequencer.** U802 LM339 (quad, open collector) on +5V; outputs pulled up to +3V3; all inputs inside the 0-3.5 V common-mode range up to VBUS 60 V.

| part | function |
|---|---|
| A (OUT1) -> BUS_GOOD_N | low when VBUS > **92 %** of VBAT_IN. VBUS divider R819 220k / R820 10k (C807 100 nF); VBAT ref R821 300k / R822 10k (C808 100 nF). |
| Q804 2N7002 | inverts BUS_GOOD_N -> BUS_EN (R825 10k pull-up) -> R808 -> INP: the main FETs are on only while the bus is good. |
| R823 39k (BUS_EN -> VBUS_DIV) | sticky hysteresis: once on, A releases only below **40-53 %** (VBUS 12.4 V at 30.7 V pack, 17 V at 36 V, 22 V at 42 V). Normal load dips cannot open the bus. |
| D801 BAT54C + R826 10k | PRECHG_EN (-> R809 -> INP_G, precharge FET Q803) is high while the bus is NOT good, pulled low (~0.45 V) by A when it is good. |
| B (OUT2) | precharge timeout: pulls PRECHG_EN low when PRE_TMR > SEQ_REF. |
| PRE_TMR R827 220k / C809 2.2 uF | 0.18 s = R C ln(3.3 / (3.3 - 1.03)). Held low while the bus is good (D801) or while the pack is low (C). |
| C (OUT3) | holds PRE_TMR low while BUS_UVLO < SEQ_REF, i.e. pack < 26 x 1.03 = **26.8 V**. This is below the TPS falling threshold on purpose: the timeout can never be disabled while the TPS is on. |
| SEQ_REF R828 22k / R829 10k (C810) | 1.03 V. Unit D unused (IN+ GND, IN- SEQ_REF, OUT open). C811 100 nF decoupling. |

**Behaviour.**
- **Power-up.** Pack >= 30.7 V and +3V3 up -> INP_G high -> precharge through R803/R804 (20 R; tau ~20 ms with ~1 mF). BST needs ~36 ms first (470 nF at 100 uA). At 92 % (~60-90 ms) INP goes high and INP_G low.
- **OC/SC trip.** VBUS collapses -> INP drops, which resets the TPS fault counter -> one precharge attempt of 0.18 s.
  - A shorted bus never reaches 92 %, so precharge stops at the timeout and stays off (latched) until the pack is reconnected.
- **Pack sag below 28.9 V.** The TPS turns off. If the pack comes back >= 30.7 V the bus restarts by itself: directly while VBUS is still above the sticky threshold, otherwise through a new precharge.
- **Pack stuck at 26.8-30.7 V at plug-in for > 0.18 s** (nearly empty): the timer latches; reconnect the pack after charging.
- BUS_FLT_N (PD8) and BUS_IMON (mux A5) are unchanged.

**Check before fab.** R803/R804 must survive one 0.18 s pulse into a shorted bus: 42 V / 20 R = 2.1 A, 88 W total, ~16 J (8 J each). Get the anti-surge part's single-pulse curve; if it is short, use a larger resistor or a shorter timer (R827).

**Firmware:** none needed. The STM32 can no longer open the bus (not requested). A later option: an open-drain STM32 pin on BUS_GOOD_N would force precharge mode / bus off.

## 3. Protected I/O header (ESC_MCU)
- All pins were free; checked against the generator's pin map and the netlist.
- **J704 JST PH B8B-PH-K vertical**, the same family as J304/J703.
  - Pin 1: +3V3_HDR.
  - Pins 2-7: PE0, PE1, PE2, PD15, PA15, PB13.
  - Pin 8: GND.
- Each signal has a 100 R series resistor (R715-R720) on the MCU side.
- ESD: 3x **USBLC6-2SC6** (U708-U710, 2 lines each, the part already used for U201), on the connector side. VBUS pin on +3V3_HDR.
- +3V3_HDR = logic +3V3 (U2) through **F701 200 mA PTC**, plus C728 100 nF.
  - This keeps a header short off +3V3_ESC (the STM32 rail).
  - Side effect: a hard short can sag U2, which feeds the E-stop loop; the drives then stop (safe direction).
- PA15 is JTDI after reset (SWD still works; firmware takes it as GPIO).

## 4. IMU (ESC_MCU)
- **U711 LSM6DS3TR-C**: KiCad `Sensor_Motion:LSM6DS3` symbol (same pinout), footprint `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y`.
- I2C1: PB8 = SCL, PB9 = SDA, with R713/R714 4.7k pull-ups to +3V3_ESC.
- Pins: SA0 (pin 1) = GND (address 0x6A); CS = VDDIO (I2C mode); aux SDx/SCx = GND; INT1 -> **PE4**; INT2 and pins 10/11 open.
- Supply: VDD/VDDIO on +3V3_ESC, with C726 100 nF + C727 1 uF.
- Place it near the board centre, away from the phase pours and the buck inductors.

## 5. +5V_AUX 2 A output (Power sheet)
- Injected into the hand-drawn Power.kicad_sch by the new `bl/aux5v.py` (re-runnable). The sheet paper went A3 -> A2; the block sits below the old drawing.
- **U901**: a copy of U1, the same symbol, footprint and values. Parts:
  - LMR36520FADDA, input from +BATT (before the breaker, behind F1 10 A);
  - C901/C902 4.7 uF/100 V 1206, C903 100 nF/100 V;
  - C904 1 uF VCC, C905 100 nF BOOT;
  - L901 15 uH SRP7028A;
  - R901 100k / R902 24.9k (5.02 V);
  - C906/C907 22 uF 1206, C908 1 uF.
  - PG is open, like U1. #FLG901 is on 5V_AUX_BUCK.
- **U902 MIC2009YM6** eFuse (EN active high, tied on).
  - R905 124 R: limit 2.0 A typ (1.69-2.31 A, CLF 210-286 V; the part's maximum is 2.0 A).
  - FAULT/ -> **AUX5_FLT_N** (R906 10k to +3V3) -> **STM32 PD11** (extra, a free pin).
  - C909 1 uF in, C910 10 uF out.
- **D901 SMAJ5.0A** TVS, then **J511 "5V_AUX"** (Phoenix MKDS-1,5-2-5.08, the old J511 footprint; pin 1 +5V_AUX, pin 2 GND).
- Net class: +5V_AUX, 5V_AUX_BUCK and U901_SW -> Power_LV (0.5 mm).
- **Margin: none.**
  - LMR36520 is rated 2 A continuous, so a 2 A load runs it at 100 % of its rating (~1.5-1.8 W at 42 V in). The eFuse can let through up to 2.31 A; above that the buck's own current limit and hiccup take over.
  - **No pin-compatible higher-current sibling is usable.** LMR36520 is the top of its 65 V family. The pin-compatible LMR33630 (3 A) / LMR33640 (4 A) are 36 V parts and do not survive a 42 V pack.
  - Proposal if 2 A must be continuous with margin: **TPS54360B** (60 V, 3.5 A, DDA, LCSC C524806, 58.9k in stock; the removed U512 12 V design has its values in `aux_design.md`). Not pin compatible: a re-layout of this block.
- **Sourcing:** LMR36520FADDA (U1 **and** U901) and SRP7028A-150M are **not in the JLC parts database** (neither in nor out of stock). Order them separately, or switch both bucks.

## Parts and LCSC (JLC local DB, 2026-10-24)
| ref | value | LCSC | type / stock |
|---|---|---|---|
| U802 | LM339DR SOIC-14 | C7948 | extended, 40.6k |
| Q804 | 2N7002 | C8545 | basic |
| D801 | BAT54C | C14308 (BAT54CLT1G) | extended, 238k |
| U711 | LSM6DS3TR-C | C967633 | extended, 21k |
| J704 | B8B-PH-K-S | C157974 | extended, 14.9k |
| U708-U710 | USBLC6-2SC6 | C21713975 | extended, 25.6k |
| F701 | SMD1206P020TF 200 mA | C20984 | extended, 80.9k |
| U902 | MIC2009YM6-TR | C625659 | extended, 248 only ($2.35) |
| D901 | SMAJ5.0A | C113952 | extended, 536k |
| U901 | LMR36520FADDA | not found | (as U1) |
| L901 | SRP7028A-150M | not found | (as L1) |
| R905 | 124 R 0603 | C100742 | extended, 5k |
| others | 0603 resistors (10k C25804, 220k C22961, 300k C23024, 12k C22790, 22k C31850, 39k C23153, 4.7k C23162, 100 R C22775, 100k C25803); 24.9k as R5; caps 100 nF / 1 uF / 2.2 uF 0805 / 10 uF 0805 / 22 uF 1206 / 4.7 uF 100 V 1206 as the existing ones | basic | |

No part in the project carries an LCSC field; none was added (report only).

## Pins used (U701) and still free
- **Used now:** PD9 BRK_FLT_N, PD11 AUX5_FLT_N, PB8/PB9 I2C1, PE4 IMU_INT1, PE0/PE1/PE2/PD15/PA15/PB13 header.
- **Still free:** PA10, PB2, PB5, PC14, PC15, PD5, PD6; mux A6.

## Files
- **Changed**
  - `ESC_MCU.kicad_sch` (regen_esc_mcu.py from the edited `bl/esc2.py`);
  - `Bus_Breaker.kicad_sch` (new `bl/breaker.py`);
  - `Power.kicad_sch` (new `bl/aux5v.py`);
  - `Brakes.kicad_sch` (one text);
  - `abx-symbols.kicad_sym` (+abx:LM339DR, single-unit; breaker.py adds it);
  - `abx-motion-brushless.kicad_pcb` (f8.py);
  - `abx-motion-brushless.kicad_pro` (3 netclass patterns).
- **Scripts:**
  - `bl/f8.py`: the staging column now starts right of the parts already off-board;
  - `bl/aux.py`: Brakes note text only;
  - `bl/fuses.py` was not edited; its Bus_Breaker section is now **stale**, so use breaker.py.
- **Not touched:** the U511 24 V block, ESC_Channel, root sheet.

## Open / owner
1. R803/R804 pulse rating (above).
2. 2 A margin on U901 and LMR36520 sourcing (above).
3. Place and route the 55 staged parts:
   - sequencer near U801;
   - IMU at the centre;
   - J704 on an edge near U701;
   - U901 block + J511 on an edge near +BATT.
4. Firmware/hwconf:
   - PD9 / PD11 fault inputs;
   - I2C1 PB8/PB9 + PE4 for the IMU;
   - header GPIO.
5. Optional: give the STM32 a way to force the bus off (open-drain pin on BUS_GOOD_N).
