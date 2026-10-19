# Project: ABX-Motion Robotics Controller (KiCad 9.0)
Path: `/home/daniel/Documents/kicad/abx-motion/abx-motion.kicad_pro`

## System Overview
12V–32V Battery-powered ESP32-S3 robotics motherboard with:
- Dual 100W Brushed DC Servo Channels (DRV8701ERGER + 4x 60V MOSFETs each + Quadrature Encoders)
- Dual Stepper Channels (2x StepStick sockets for DRV8825/TMC5160 + external terminal breakout)
- Dual 5V Relay Outputs (Omron G5LE-14-DC5 + AO3400A MOSFET drivers)

## Hierarchical Schematic Structure
Root sheet `abx-motion.kicad_sch` has 5 sub-sheet blocks:
1. `Power_Supply` (`Power.kicad_sch`)
2. `MCU_and_Encoders` (`MCU.kicad_sch`)
3. `DC_Motor_1` (`Motor_Channel.kicad_sch`)
4. `DC_Motor_2` (`Motor_Channel.kicad_sch` - second instance of same file)
5. `Steppers_and_Relays` (`Steppers_Relays.kicad_sch`)
Use global KiCad power symbols: `+BATT` (protected 12-32V), `+5V`, `+3V3`, `GND`.

## Sheet 1: Power.kicad_sch (Locked-In BOM & Netlist)
- `J1`: `Connector:Conn_01x02_Pin` (XT60_BAT, `Connector_AMASS:AMASS_XT60-M_1x02_P7.20mm_Vertical`)
- `F1`: `Device:Fuse` (25A, `Fuse:Fuse_Blade_ATO_directSolder`) between J1+ and Q1 Drain (Pin 3).
- `Q1`: `Device:Q_PMOS_GDS` (AONS21357 60V P-MOSFET, `Package_TO_SOT_SMD:TDSON-8-1`). Drain=Input, Source=`+BATT`.
- `D1`: `Device:D_Zener` (BZX84-C12, `Diode_SMD:D_SOT-23_ANK`) Cathode to `+BATT`, Anode to Q1 Gate.
- `R1`: `47k` (`Resistor_SMD:R_0603_1608Metric`) from Q1 Gate to `GND`.
- `D2`: `Device:D_TVS` (SMCJ33A, `Diode_SMD:D_SMC`) Cathode to `+BATT`, Anode to `GND`.
- `R2` (`100k`) & `R3` (`10k`) + `C1` (`100nF`): Voltage divider from `+BATT` to `GND`, midpoint -> Hierarchical Output `VBAT_SENSE`.
- `U1`: `Regulator_Switching:LMR33630ADDA` (Value=`LMR36520FADDA` 65V->5V 2A Buck, `Package_SO:Texas_HSOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.95x4.9mm_ThermalVias`).
  - VIN (Pin 2) & EN (Pin 3) -> `+BATT` with `C2,C3` (2x 4.7uF 50V 1206) + `C4` (100nF 50V 0603).
  - VCC (Pin 6) -> `C5` (1uF 16V 0603) to `GND`.
  - BOOT (Pin 7) -> `C6` (100nF 50V 0603) to SW (Pin 8).
  - SW (Pin 8) -> `L1` (15uH, `Inductor_SMD:L_Bourns_SRP7050TA`) -> `+5V` with `C7,C8` (2x 22uF 16V 1206).
  - FB (Pin 5) -> Midpoint of `R4` (100k to `+5V`) and `R5` (24.9k to `GND`).
- `U2`: `Regulator_Linear:AP2112K-3.3` (`Package_TO_SOT_SMD:SOT-23-5`), steps `+5V` (`C9` 1uF) to `+3V3` (`C10` 10uF 0805).
- Add `power:PWR_FLAG` to `+BATT` and `GND`.

## Sheet 2: MCU.kicad_sch (ESP32-S3-WROOM-1 & 74LVC14A)
- `U3`: `ESP32-S3-WROOM-1` with USB-C (`GPIO19` D-, `GPIO20` D+, 2x 5.1k CC resistors, USBLC6-2SC6), Reset (`EN`) & Boot (`GPIO0`) buttons.
- Pin Map:
  - `GPIO1`: `VBAT_SENSE`
  - Motor 1: `GPIO4` (`M1_PWM_PH`), `GPIO5` (`M1_PWM_EN` w/ 10k pulldown), `GPIO6` (`M1_CS`), `GPIO7` (`M1_nFAULT`)
  - Encoder 1: `GPIO15` (`ENC1_A`), `GPIO16` (`ENC1_B`)
  - Motor 2: `GPIO17` (`M2_PWM_PH`), `GPIO18` (`M2_PWM_EN` w/ 10k pulldown), `GPIO8` (`M2_CS`), `GPIO2` (`M2_nFAULT` - avoids GPIO3 strap)
  - Encoder 2: `GPIO9` (`ENC2_A`), `GPIO10` (`ENC2_B`)
  - Steppers: `GPIO11/12` (STEP1 PUL/DIR), `GPIO13/14` (STEP2 PUL/DIR), `GPIO21` (`STEP_ENABLE` w/ 10k pullup to +3V3)
  - Relays: `GPIO47` (`RELAY_1` w/ 10k pulldown), `GPIO48` (`RELAY_2` w/ 10k pulldown)
- `U4`: `74LVC14A` powered at `+3V3`. Filters 4 encoder channels (each has 4.7k pullup to `+5V` -> 1k series R -> 1nF cap to `GND` -> Schmitt input). Tie unused inputs (Pins 11, 13) to `GND`.

## Sheet 3: Motor_Channel.kicad_sch (DRV8701ERGER + 4x CSD18540Q5B 60V MOSFETs)
- `U_DRV`: `DRV8701ERGER` (VQFN-24).
  - CRITICAL: `VCP` (Pin 2) 1uF 16V cap connects to `VM` (Pin 1), NOT GND!
  - `CPH` (Pin 3) to `CPL` (Pin 4): 100nF 50V cap.
  - `VREF` (Pin 6): 18k to `AVDD` (Pin 7, 4.8V) and 30k to `GND` (= 3.0V -> 15A hardware chop limit with 10mOhm shunt).
  - `nSLEEP` (Pin 13): 10k pullup to `+3V3`.
  - `IDRIVE` (Pin 12): Tied to `GND`.
  - `SO` (Pin 11): 1k series isolation resistor BEFORE 10nF ADC filter cap to `GND`.
  - 4x `CSD18540Q5B` (60V N-MOSFETs) with 10 Ohm gate resistors, 220uF 50V electrolytic + 2x 4.7uF 50V ceramic on `+BATT`, 10mOhm 2W 2512 Kelvin shunt (`SP`/`SN`), and 10 Ohm + 10nF 100V RC snubber across motor outputs.

## Sheet 4: Steppers_Relays.kicad_sch
- 2x StepStick sockets (compatible with DRV8825/TMC5160 36V+ modules, 100uF 50V cap on `+BATT` each) + parallel 4-pin screw terminals for external drivers.
- 2x Omron `G5LE-14-DC5` (5V coil) driven by `AO3400A` N-MOSFETs, `1N4148WS` flyback diodes, status LEDs, and 3-pin 5.08mm output terminals.

## Workflow & Cost-Efficiency Rules
- **Batch via Python Scripts Over Individual MCP Calls:** Never make dozens of sequential MCP tool calls to place components, wires, or footprints one by one. Instead, write clean, repeatable Python scripts (reading stock symbol definitions directly from `/usr/share/kicad/symbols/` and manipulating S-expressions or `pcbnew`) to generate/update schematic sheets and footprints in a single turn.
- **Use MCP / `kicad-cli` for Verification:** Only use individual MCP calls or `/usr/bin/kicad-cli` to verify ERC/DRC, export SVG/PNG renders, and inspect the results.
