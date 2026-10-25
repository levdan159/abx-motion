# ESP32 / Industrial_IO / Sensors + 12 V buck removal (2026-10-24)

Board `abx-motion-brushless`, branch `v1.0-bl-wip`. Nothing committed. KiCad was closed for every write.

## Result
- **Schematic: ERC 0 errors** (before 0). 288 parts (before 421).
- **PCB: parity 0, no clearance / short / courtyard / hole errors.** New airwires only.

## Parts removed (135)
- **MCU_and_Encoders** (ESP32 sheet, 67 removed): C201-C218, D201, H5, H6 (M2 OLED holes), J202, J203 (encoders), J206, J207 (RS-485), J208 (OLED), J209 (I2C_EXP), LED201-LED203, R203, R206, R211-R218, R220-R235 (except R219), SW201-SW205, U3 (ESP32-S3), U4 (74LVC14), U202 (TCAN1042), U203 (THVD1450), U205/U206 (MIC2009).
- **Industrial_IO** (45, whole sheet): C601-C611, D601, D602, J601-J606, Q601, Q602, R601-R620, R623, R624, U601 (PCA9555), U602 (MIC2009).
- **Sensors** (2, whole sheet): J210 GPS, J211 IMU.
- **Brakes, 12 V block** (21, taken from the netlist): U512 TPS54360B, L521, D521, C534-C537 (U512 VIN caps on +BATT/GND), C538 CZ, C539 Chf, C540 BOOT, C541-C543 out, R526/R527 UVLO, R528 RT, R529/R530 FB, R531 Rcomp, J511 12V_OUT, J512 BRK_VSEL.
- D523 (SS54) anode is now on **+24V** directly. The old BRK_VSEL copper became +24V and was trimmed to D523: 1 new +24V airwire.
- J510 value is now `24V_OUT (to v1.2 board)`.
- Net classes: removed `+12V` and `/Brakes/BRK_VSEL` from the Power_HV patterns.

## Parts kept and moved to ESC_MCU (same refs, values and footprints; PCB positions unchanged)
- **CAN**
  - J205 CAN_BUS: 1 CAN_H, 2 CAN_L, 3 GND.
  - J204 CAN_TERM + R219 120R, on U704.
- **USB-C**
  - J201, U201 USBLC6-2SC6, R201/R202 5.1k CC pull-downs.
  - F2 500 mA PTC + D202 B5819W: USB can still power +5V on the bench.
- **New: VBUS sense divider into PA9.** R711 10k (VBUS_USB to USB_VBUS_SNS) and R712 20k to GND: 5.0 V reads 3.33 V (PA9 is 5 V tolerant). R711/R712 are staged off-board at (225, 60) / (225, 72), not placed.
- **Note: J201 / J205 / J204 still sit in the old ESP32 corner (x 49-61, y 54-85), about 70 mm from U701.** Move them toward the STM32 before routing USB.
- **Net renames.** CAN_H, CAN_L and NRST are now local nets on ESC_MCU: `/ESC_MCU/CAN_H`, `/ESC_MCU/CAN_L`, `/ESC_MCU/NRST`.
  - Why: with the ESP32 block gone, the root stub labels dangled (3 ERC errors).
  - The root ESC_MCU block lost those 3 pins. Copper was re-netted, so routes are kept.
  - critical.py now routes `/ESC_MCU/NRST`.

## STM32 U701 pin map changes
| pin | net | was (ESP32) |
|---|---|---|
| PE5 (TIM9 CH1) | /BRAKE1_EN -> U513 IN1 | IO11 |
| PE6 (TIM9 CH2) | /BRAKE2_EN -> U513 IN2 | IO12 |
| PD10 (in) | /ESTOP_SENSE (R507 1k from +3V3_DRV_EN) | IO13 |
| PD8 (in) | BUS_FLT_N (R812 10k pull-up to +3V3 kept) | IO48 |
| PA11 / PA12 | USB_DM / USB_DP (via U201) | IO19/IO20 |
| PA9 | USB_VBUS_SNS (R711/R712) | - |
| U706 A4 (mux 100, "EXT2") | /VBAT_SENSE (100k/6.8k, 42 V -> 2.67 V, 48 V -> 3.06 V: fits 3.3 V) | IO? ADC (was tied to GND) |
| U706 A5 (mux 101, "EXT1") | BUS_IMON (30.6 mV/A, 60 A -> 1.84 V; >~105 A only before the 80 A / 5 ms trip, R814 1k limits clamp current) | IO6 (was tied to GND) |

- ESC_NRST: SWD only (J701 pin 4), C715 100 nF kept. There is no external pull-up (the STM32's internal one is used).
- ESTOP_OK stays on PE15.
- ESTOP_SENSE (PD10) and ESTOP_OK (PE15) now read the same signal (+3V3_DRV_EN) on two pins. R507 could go later.
- Still free: PA10, PA15, PB2, PB5, PB8, PB9, PB13, PC14, PC15, PD5, PD6, PD9, PD11, PD15, PE0, PE1, PE2, PE4; mux A6.

## ERC (kicad-cli, all severities)
| type | before | after |
|---|---|---|
| errors | 0 | 0 |
| lib_symbol_mismatch (warn) | 13 | 10 |
| multiple_net_names VBAT_IN/V_RAW_IN (warn, old) | 1 | 1 |
| isolated_pin_label (warn): global BUS_EN, PRECHG_EN | 0 | 2 |

## DRC (`--schematic-parity`, all severities, zones refilled)
| type | before | after |
|---|---|---|
| clearance / shorting / courtyard / hole | 0 | 0 |
| starved_thermal (error) | 10 | 9 |
| lib_footprint_mismatch | 125 | 36 |
| silk_over_copper / silk_overlap | 199 / 199 | 199 / 199 |
| silk_edge_clearance | 6 | 3 |
| unconnected | 79 | 82 |
| parity | 0 | 0 |

**starved_thermal.** Gone: U706 pad 2, LED203. New: U2 pad 2 (GND, F.Cu, 1 spoke).

**Unconnected.**
- New airwires (all expected):
  - PE5/PE6 BRAKE1/2_EN, PD10 ESTOP_SENSE, PD8 BUS_FLT_N;
  - USB_DM, USB_DP, USB_VBUS_SNS x2, VBUS_USB (R711/R712 staged);
  - VBAT_SENSE and BUS_IMON to U706;
  - +24V to D523.
- Gone: GND 13 -> 11, BUS_EN, PRECHG_EN, BRK_FLT_N (now one-ended or routed).

## PCB copper work (real board; backup `bak/pre_esp_removal/abx-motion-brushless.kicad_pcb`)
1. **`bl/f8.py`**
   - It now re-paths a symbol that moved to another sheet (same ref + footprint), keeping footprint, position and copper.
   - It moves the copper of a net whose pads all went to one new net (GUI F8 behaviour).
   - Stage area moved to x 225, off the widened board.
   - Takes an optional board path. Result: 135 footprints removed, 2 added, 9 re-pathed, 13 nets' copper re-netted.
2. **New `bl/espclean.py <board> --baseline <pre-F8 board> [--drc drc.json]`** (idempotent: a 2nd run deletes nothing). It deleted:
   - 1191 tracks/vias on nets with no pads;
   - 9 U512 pours: PWR_SW_12, PWR_12V_F/B, PWR_GND_U512, PWR_GND_EP_U512_F+GND_P7, PWR_GND_EP_U512_B, PWR_BATT_U512/C536/R526;
   - 15 PWR_VIAS vias inside those pours;
   - 2 GND tracks on U706 pad 1 (now VBAT_SENSE);
   - 279 dangling tracks and 52 dangling vias, trimmed repeatedly.
3. **Protected groups.** Only 12 V copper left them:
   - critical_routes 439 -> 424: the 15 U512 FB/COMP/CZ/EN/RT/BOOT segments;
   - PWR_VIAS 556 -> 535: 6 on +12V, 15 in the U512 pours;
   - PWR_ zones 67 -> 58.
   - The 6 U512 pours on +BATT/GND were removed too (they only served U512 pads). Nothing else in those groups changed.
4. **Scripts** buckplace.py, critical.py and pours.py no longer have U512 / 12 V entries.
   - Run on a copy (`buckplace -> critical -> pours`): 16 parts placed, 0 problems; critical 55/55 routed (was 64, less 9 U512 routes); pours 58 zones, 535 vias.
   - DRC on that copy is identical to the real board.
   - **They were not re-run on the real board** (not needed: espclean removed the 12 V copper).
   - fill.py now takes an optional board path.

## Remaining +3V3 users (U2 AP2112K kept)
- J102 pin 1 (E-stop loop source -> +3V3_DRV_EN: DRV enable, brake nSLEEP, ESTOP_OK/SENSE).
- R533 (DRV8874 VREF divider) and R537 (PMODE).
- R510 (BRK_FLT_N pull-up) and R812 (BUS_FLT_N pull-up).
- R8 + LED_PWR_3V3_1 (3V3 LED), TP_3V3_1, C10 (U2 output cap).
- The In2 `+3V3` plane (left column x 45.5-100) now has almost no users.
- Option for later: move these to +3V3_ESC and drop U2 (the E-stop loop then runs from the ESC rail).

## Dangling nets / proposals
- **BUS_EN, PRECHG_EN**: one pin each (R808/R809). Note on the Bus_Breaker sheet: "TODO: hardware-autonomous enable/precharge (next step)". ERC: only 2 isolated_pin_label warnings. The INP/INP_G internal pull-downs keep the bus OFF.
- **BRK_FLT_N** (DRV8874 nFAULT, R510 pull-up): it lost the PCA9555 IO1_3 input. Proposal: STM32 PD9 (input).
- **EFUSE_EN / EFUSE_FLT_N**: no parts left (all MIC2009 removed); the nets are gone.
- **Lost functions (not replaced, by design)**: odometry encoders J202/J203, RS-485, OLED + buttons, GPS/IMU connectors, the PCA9555 I/O (limit inputs, 2 low-side outputs), the CAN status LED, the +5V_ENC / +3V3_EXT / +5V_OUT switched rails.
- **Stale sheet text** (history): ESC_Channel ("Odometry encoders go to the ESP32"), Bus_Breaker header notes (ESP32 mentions; a new line points at PD8 / the U706 mux).

## TODOs
1. Hardware-autonomous breaker enable + precharge (BUS_EN, PRECHG_EN).
2. I/O header (spare STM32 pins: limit switches, encoders, BRK_FLT_N).
3. IMU (if wanted, on spare I2C/SPI pins).
4. 5 V aux output (the old +5V_OUT / +5V_ENC eFuses are gone).
5. 6 A 24 V buck (U511 is 4 A continuous / 5 A peak).
6. Move J201/J205/J204 near U701, place R711/R712, route the new airwires.
7. Firmware/hwconf: brake PWM on TIM9, ESTOP_SENSE PD10, BUS_FLT_N PD8, mux ch4/ch5 = VBAT / IMON, USB OTG_FS PA11/12 (+ PA9 VBUS).

## Files
- **Changed**
  - Schematic: `abx-motion-brushless.kicad_sch` (root), `Brakes.kicad_sch` (aux.py), `ESC_MCU.kicad_sch` (regen_esc_mcu.py), `Bus_Breaker.kicad_sch` (2 text lines injected), `Power.kicad_sch` (F1 note text via aux.py).
  - Project and board: `abx-motion-brushless.kicad_pro` (aux.py), `abx-motion-brushless.kicad_pcb`.
- **Moved to backup**: `MCU.kicad_sch`, `Industrial_IO.kicad_sch`, `Sensors.kicad_sch` -> `.claude/handoff/bak/pre_esp_removal/`.
- **Scripts** (`.claude/handoff/bl/`):
  - edited: aux.py, esc2.py (ESC_MCU section, guarded MCU-sheet edit, root pin list), critical.py, buckplace.py, pours.py, f8.py, fill.py, fuses.py (TODO text);
  - new: espclean.py.
- **Backups**: `.claude/handoff/bak/pre_esp_removal/` holds every .kicad_sch, .kicad_pcb, .kicad_pro and abx-symbols.kicad_sym, plus `bl/` with the original scripts. `fuses.py` there was rebuilt from the git index copy, which equals the pre-edit file.
