# ABX-Motion Robotics Controller (KiCad 9.0)

**12V–32V Battery-Powered ESP32-S3 Industrial & Mobile Robotics Motherboard**

![3D Top View](renders/pcb_3d_top.png)
![3D Bottom View](renders/pcb_3d_bottom.png)

## System Overview
- **MCU & Connectivity:** `ESP32-S3-WROOM-1-N8R2` with USB-C (`USBLC6-2SC6` ESD + tightly-coupled 90Ω differential pair), isolated-ready CAN 2.0B (`TCAN1042HGVDRQ1`), RS-485 (`THVD1450DR` with `SMBJ6.5CA` TVS & `330Ω` fail-safe bias), and `0.96"` I2C OLED (`ER-OLEDM0.96-1B-I2C`) + 3-button UI (`BACK`, `NEXT`, `HOME`).
- **Dual 100W Brushed DC Servo Channels:** 2x `DRV8701ERGER` full-bridge gate drivers + 8x `CSD18540Q5B` (60V, 1.8mΩ N-MOSFETs), `10mΩ 3W` (`CRA2512`) Kelvin current shunts, configurable `IDRIVE` (`200kΩ`), RC phase snubbers, and 2x 5V quadrature encoder inputs with `1kΩ/1nF` low-pass filters + `SN74LVC14ADR` Schmitt-trigger conditioning.
- **Dual Stepper Channels:** 2x StepStick sockets (`DRV8825` / `TMC2209` / `TMC5160`) with 3-channel microstep DIP switches + parallel 4-pin external industrial stepper driver headers.
- **Dual High-Current Relay Outputs:** 2x Omron `G5LE-14-DC5` (5V SPDT 10A relays) with `AO3400A` MOSFET drivers, `1N4148WS` flyback diodes, and status LEDs.
- **Power Architecture:** `XT60` battery input, `25A` automotive blade fuse, `SQJ459EP-T1_GE3` (`-60V, 52A` P-MOSFET) reverse-polarity protection, `SMCJ28A` (1500W TVS), `LMR36520FADDAR` (65V -> 5V 2A synchronous buck), and `AP2112K-3.3` LDO.
- **4-Layer PCB (`160 x 110 mm`):** `F.Cu` (Signals + High-Current Power Pours), `In1.Cu` (100% Unbroken Solid `GND` Reference Plane), `In2.Cu` (`+BATT` / `+5V` / `+3V3` Power Planes), `B.Cu` (Signals + Input Power Pours).

## Repository Structure
- `abx-motion.kicad_pro`, `abx-motion.kicad_sch`, `abx-motion.kicad_pcb`: Main KiCad 9.0 project, hierarchical schematics (`Power.kicad_sch`, `MCU.kicad_sch`, `Motor_Channel.kicad_sch`, `Steppers_Relays.kicad_sch`), and routed 4-layer PCB (`0` DRC errors, `0` ERC errors).
- `production/`: Ready-to-manufacture Gerbers, Excellon drill files, JLCPCB BOM (100% verified in-stock LCSC `C-numbers`), Pick-and-Place (`CPL`), and PDFs.
- `renders/`: High-resolution 2D/3D board and schematic renders.
