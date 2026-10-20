# ABX-Motion V1.1 prototype controller

Compact **157 × 105 mm, four-layer** ESP32-S3 motion controller. This layout is
intended for controlled prototype testing. Printed voltage, motor-power and
fuse ratings are design targets, not measured board ratings.

![Top view](renders/pcb_3d_top.png)
![Bottom view](renders/pcb_3d_bottom.png)

## Hardware

- ESP32-S3-WROOM-1-N8R2, native USB-C programming, RESET/BOOT buttons,
  CAN, RS-485, I²C OLED header and BACK/OK/FWD controls.
- Two DRV8701E brushed-motor bridges with encoder inputs, 10 mΩ shunts
  and configurable gate-drive resistors.
- Two StepStick sockets and external STEP/DIR/EN connectors. Check each
  carrier's pinout, enable polarity, voltage range and mode straps before use.
- Two SPDT relays. Contact ratings do not establish PCB current capability.
- XT60 input, Keystone 3557-2 fuse holder, reverse-polarity P-MOSFET,
  TVS3300 precision pulse clamp, 5 V buck and 3.3 V LDO.
- Front and rear exposed-copper gears (`F.Cu`/`F.Mask` and `B.Cu`/`B.Mask`)
  with white silkscreen text (`AUTOBOTIX` / `ABX-Motion V1.1`). Select ENIG for
  gold artwork.

## Compact I/O

J601–J606 use identical three-pin JST-PH headers. Read the per-pin markings:
output headers have a different function from limit headers.

| Headers | Channel | Pin 1 | Pin 2 | Pin 3 |
| --- | --- | --- | --- | --- |
| J601 | DC motor 1 limits | MIN | GND | MAX |
| J602 | DC motor 2 limits | MIN | GND | MAX |
| J603 | Stepper 1 limits | MIN | GND | MAX |
| J604 | Stepper 2 limits | MIN | GND | MAX |
| J605 | Auxiliary output 1 | +5V_OUT | GND | SW1 |
| J606 | Auxiliary output 2 | +5V_OUT | GND | SW2 |

The eight limit channels have 3.3 V pull-ups, series resistors and RC filtering.
Use dry contacts to ground or compatible 3.3 V logic. **Do not connect 12/24 V
sensors directly.** Normally closed contacts let firmware treat a broken wire
as an active limit. Configured as outputs, these are resistor-limited logic
signals, not load drivers.

Connect a 5 V auxiliary load between +5V_OUT and SW1/SW2. SW pins are low-side
MOSFET drains. Both headers share F5: **Littelfuse 1206L050/15YR, C151162**,
500 mA hold at 20 °C, 15 V. The PTC is not a precise 500 mA current limiter;
temperature, trip delay and the total 5 V supply budget constrain usable loads.

## Firmware and stopping

PCA9555 U601 is at I²C address 0x20 on GPIO41 (SDA) / GPIO42 (SCL).
Its active-low interrupt uses GPIO36; BACK uses GPIO21.
Port 0 bits 0–7 are limits in the table's MIN/MAX order.
Port 1 bits 0/1 command auxiliary outputs, bits 2/3 command active-low
stepper enables, and bit 4 reads E-stop status. Bits 5–7 are grounded and
must remain inputs.

On startup, keep both ports as inputs, write Port 1 output latch **0x0C**
(outputs off, steppers disabled), then configure Port 1 with **0xF0**. Keep
Port 0 configuration **0xFF** for limit sensing. Read inputs to acknowledge
interrupts. An ESP32 reset does not reset the independently powered expander;
reinitialize it on every boot and test reboot behavior under load. No application
firmware is supplied in this repository yet.

The hardware E-stop net disables DC bridges and gates onboard/external
stepper enables. Relays and auxiliary outputs remain powered. Verify stop
behavior with each actual attached driver. Firmware must block travel into an
active limit while allowing controlled retreat; I²C limit sensing is not an
independent hardware overtravel interlock.

## Validation and first power-up

**Manufacturing hold:** the D2 protection choice is under review; the small
TVS has substantially less long-pulse capacity than the original SMC diode.
Populating both directly in parallel does not guarantee current sharing.
See `validation/assembly-audit-20261020/review.txt` and the matched review
files in `production/assembly-audit-20261020/`. Supplier numbered-pad checks
now verify D2, U601 and all six PH connector directions. The relay supplier
CAD conflicts with Omron's hole drawing; confirm physical relay alignment
with the assembler. No new hardware changes were made in that audit.

The supply target is conventional 7S lithium ion (29.4 V fully charged), with
a 32 V normal ceiling. First power at the intended voltage needs controlled
fault energy/current, motors disconnected and drivers disabled. A 12 V test
is not required. Check rails, USB programming, expander defaults, all eight
inputs, auxiliary outputs and E-stop before adding one unloaded motor at low
current. Measure switching transients, rail ripple, current accuracy and
temperatures before increasing load. D2 is now TI TVS3300DRVR (C2863624):
33 V standoff, 40 V maximum clamp under TI's specified 8/20 us surge conditions.
The SON package rating is 35 A at 8/20 us but only 3.5 A at 10/1000 us. It is
not a continuous braking load. Regenerative loads require a battery/BMS that
accepts their charging current or a separately sized braking clamp. Do not
substitute a TMC2209 carrier for 7S/32 V use; its operating maximum is 29 V.
Q1 heating, LDO dissipation and motor-capacitor ripple capability also need
measurement. Confirm the OLED module's physical hole/header dimensions before
ordering (`H5`/`H6` M2 holes are at `23.30 mm` actual X spacing vs `23.0 mm`
nominal silkscreen callout, `23.80 mm` below `J208`); SSD1306 module names do
not guarantee a common hole pattern.

Assembly BOM correction (20 October 2026): StepStick sockets use four C27438
1x8 female strips, with 1.0 mm PCB holes per the supplier drawing. The earlier
C145755 entry was a temperature sensor and must not be assembled. The current
BOM has 66 supplier/footprint groups for 239 placements; repeated connector,
LED and switch selections are consolidated. Upload the matching new Gerbers,
BOM and CPL together. F1 is a holder; obtain the actual blade fuse separately.

Robustness revision (20 October 2026): R2=150k above R3=10k gives a nominal
**VBAT/16** ADC input. R313/R413=1k form 1:2 dividers with R304/R404; the MCU
now measures **SO/2**. Firmware must calculate shunt current using
`I = (2*Vadc - calibrated_SO_offset) / (20*0.010)` with actual gain/offset
calibration; current chopping thresholds are unchanged. R6=22k reduces battery
LED heating. All pre-existing signal routing and component positions except
D2's local footprint remain preserved. No application firmware is supplied.
Use the saved native design and the matching package. Legacy stage/router
scripts restore older checkpoints and must not be used to export this revision.
