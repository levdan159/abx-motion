# v1.2 board power interface: 24V_OUT (J510) from the brushless board (2026-10-25)

Source: brushless board `abx-motion-brushless`, Brakes sheet, buck U511 = TI LM70880RRXR (datasheet SNVSCD3,
Sept 2024). Design and verification: `lm70880_report.md`. This page is what the v1.2 board may rely on.

## 1. Connector J510
| item | value |
|---|---|
| part | Phoenix Contact MKDS 1,5/2-5,08 (1715721, LCSC C480516), green screw terminal, 2 poles, 5.08 mm |
| position | bottom board edge at (190.0, 161.0), wire entry from the bottom edge |
| pin 1 (square pad, left when the board is viewed from the top with the wire entry facing you) | **+24V** |
| pin 2 | **GND** (board ground = battery minus side of the logic supply) |
| wire | 1.5 mm² (AWG 16) for 8 A; keep the pair twisted, as short as practical |
| terminal rating | 13.5 A (IEC) per the Phoenix catalogue: not the limit here |

No reverse-polarity or reverse-current protection on the output side: J510 is a source. The brake output
(DRV8874, J501) takes its supply from the same +24V rail through D523.

## 2. Ratings
| item | value |
|---|---|
| output voltage | 24.0 V (+-2 % with 1 % resistors and the 0.8 V +-0.75 % reference) |
| input range (pack) | 25-42 V (10S); regulates down to about 25.1-25.6 V input, below that the output tracks the input (about 99 % duty) |
| start / stop (buck UVLO) | on at 27.7 V (26.3-29.1 V), off at 24.9 V pack |
| **continuous current** | **6 A** for the whole +24V rail (J510 + the brake supply through D523) |
| **short-term current** | **8 A** for minutes (junction about 125-140 C at 45 C ambient; no time limit is enforced by hardware below the current limit) |
| peak current limit (inductor, cycle by cycle) | 10.0 / 11.2 / 12.4 A (min / typ / max) = about 9.2 / 10.4 / 11.6 A average out at 36 V in |
| ripple | about 25 mV p-p at 8 A (5x 10 uF X7R + 47 uF bulk on the input side) |
| soft start | 2.8 ms (1.9-4.4 ms) internal; no pre-bias discharge |
| switching | 500 kHz, spread spectrum on (+-8 %), forced PWM (it can also sink current, see 4) |
| power-good | not wired (PG of U511 is open); the v1.2 board must make its own +24V UVLO decision |

The brake output shares the rail: a released coil brake takes up to about 1.5 A continuous (DRV8874 trips at
3 A). **Budget for v1.2 = 6 A minus the brake current continuous (4.5 A with the brakes held released), 8 A minus
the brake current short-term.** If v1.2 needs 6 A continuous of its own, the brake current must come off the rail
(see `buck24_6a_design.md`: 7.5 A rail) and F1 must go to 15 A (section 5).

## 3. Overload behaviour (what v1.2 will see)
1. **Cycle-by-cycle limit** at 10.0-12.4 A inductor peak. The output voltage then sags to I_lim x R_load.
2. **No shutdown while +24V stays at or above 12 V**: hiccup only starts when FB < 0.4 V (output < 12 V) for 512
   consecutive current-limited switching cycles (about 1 ms). Four clean cycles reset the count. A stalled motor
   that holds the rail at 15-20 V is therefore fed at the limit (about 10 A) until it moves or the IC heats up.
3. **Hiccup** (output < 12 V for 512 limited cycles): switching stops for 16384 cycles (33 ms), then a new 2.8 ms
   soft start, repeating. Hiccup is disabled during soft start, so a large capacitive load rides the current limit
   instead of tripping.
4. **Thermal shutdown** at 175 C junction, restart 15 C lower (non-latching).
5. **Output over-voltage**: if +24V is pushed above 110 % (26.4 V) the buck turns its low-side FET on to pull the
   output down, and in forced PWM it sinks current back to the pack (negative limit 30 mV / 5 mOhm = about 6 A).
   **v1.2 must not back-feed +24V**: motor regeneration has to be absorbed on v1.2 (bus capacitor + brake chopper or
   TVS, or an ideal-diode / reverse-current block on its input). The buck's BIAS pin is grounded, so back-feed cannot
   damage U511 below 55 V, but it can trip the OV discharge and heat the converter.

## 4. Requirements on the v1.2 board
- **DC-motor start current**: the DRV8701 current regulation (VREF / sense resistor chopping) must keep the sum of all
  motor currents plus v1.2 logic **at or below 8 A for start-up and at or below the continuous budget (section 2)**.
  Set the DRV8701 chop limit per motor so that the worst simultaneous start stays under 8 A; do not rely on the buck's
  current limit as a motor limit (it lets the rail sag, which resets v1.2 logic).
  - Design hint: DRV8701 chop current I_CHOP = V_VREF / (A_V x R_SENSE) with A_V = 20 V/V (check against the DRV8701
    datasheet revision used); leave about 10 % margin for R_SENSE, VREF and amplifier tolerance.
- **Input capacitance on +24V (v1.2 side)**: at most about 470 uF total, or hold the motor drivers off until +24V is up.
  Soft-start charge current is C x 24 V / 1.9-4.4 ms: 470 uF -> 2.6-5.9 A on top of the load.
- **Logic supply on v1.2**: give it its own UVLO (for example 20 V on / 18 V off): during a limit-induced sag the rail
  can sit anywhere between 12 V and 24 V for seconds.
- **No back-feed** (section 3.5): +24V must never be driven above 26 V from the v1.2 side, also not with the pack
  disconnected (the brushless board would then be powered backwards through U511's high-side body diode).
- **Ground**: return all v1.2 current through J510 pin 2; do not create a second ground path to the brushless board
  through signal cables carrying amperes.

## 5. Upstream path on the brushless board (for reference)
- +BATT -> F1 (10 A, 58 V ATO) -> Q1 (SQJ459EP) -> U511. At 8 A out the input is about 6.0 A at 36 V and 8.6 A at
  25 V (with about 0.7 A of logic): inside a 10 A ATO for minutes, marginal for hours at a low pack. 6 A continuous
  needs at most 6.6 A in: fine. **For 8 A continuous, change F1 to 15 A** (owner decision; Power sheet).
- +24V from the shunt R538 to J510 runs on the In2 +24V plane (about 20 mm wide, 1 oz): fine for 8 A. J510 pin 1 is
  connected to that plane only by thermal spokes (0.4 mm, In2): change the pad to a solid connection or add an outer
  layer +24V pour to J510 before fab (open item in `lm70880_report.md`).
