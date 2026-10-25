# U511 LM70880: can it run 7.5 A continuous at +24 V? (2026-10-25, research only, nothing on the board edited)

Conditions: 10S pack, 25-42 V in. Output 24.0 V. fsw 500 kHz. L520 TMPC1265HP-100MG-D. RS 5 mOhm. BIAS = GND.
Ambient 45 C, free air.

Stack-up (read from the board, not assumed): F.Cu / B.Cu are 70 um (2 oz), In1 / In2 are 35 um (1 oz), 1.6 mm total.
Only the buck heats the board in this model. ESC heat, enclosure air and neighbouring parts add on top.

## Verdict
- **6 A continuous: yes.** Worst case is about 110 C at 42 V, and about 120 C even with poor copper.
- **7.5 A continuous, layout as planned now: no, if the target is Tj <= 125 C.**
  - About 128 C at 36 V and 134 C at 42 V.
  - It is still under TI's 150 C operating limit and the 175 C thermal shutdown. So 7.5 A runs, with about 15 C of margin to TI's limit and none to ours.
- **7.5 A continuous: yes, under conditions.** It needs the copper and vias in section 4, plus a bench check. The model then gives 116-125 C at 42 V, so the margin is small.
  - It also needs **F1 at 15 A** and **J510 pad 1 connected solid** (section 5).

## 1. Sources and how the losses were derived
The datasheet (TI SNVSCD3) gives no RDS(on). Three TI sources were used instead:
- **TI quickstart calculator `LM70XX0-CALC`** (A1 .xlsm, ti.com). It contains TI's loss model and values for this part:
  - HS 24 mOhm, LS 18 mOhm (8 V VCC setting), temperature coefficient 0.7 %/C.
  - tr = tf = 3 ns, Coss 250 / 350 pF, Qoss 3 nC, Qg 3 + 4.1 nC.
  - Dead time 14 ns, body diode Vsd 0.8 V, Qrr 30 nC at 8 A.
- **Validation of that model:**
  - At 48 V -> 12 V, 8 A, 400 kHz with RDS(on) taken at Tj = 150 C, the model gives **3.60 W**.
  - The datasheet derating curve (Fig 7-7: 8 A up to Ta = 83 C, RthJA 18.6) implies (150 - 83) / 18.6 = **3.60 W**. They agree.
  - At part load the model reads 0.2-0.4 W low. A fit to the whole curve adds a fixed 0.58 W (scaled with Vin x fsw): P_IC = 0.58 (Vin/48)(fsw/400k) + 0.87 x model, accurate to ±0.15 W.
  - **The figures below use whichever of the two is higher.**
- **EVM (SNVU872A):**
  - 6-layer board, every layer 2 oz, about 104 x 78 mm.
  - Thermal image at 48 V -> 5 V, 8 A, 25 C: case maximum 87.4 C, at an IC loss of about 3.4 W (90.5 % efficiency).
  - That is about 18.5 C/W, which matches RthJA 18.6.
  - Other thermal metrics: psiJT(Tcase-max) 0.8 C/W, psiJB 6.3 C/W.
- **Low line:**
  - At 25 V the duty cycle needs to be about 0.976. That is above the 88 ns minimum off-time limit (0.956 at 500 kHz), so the part skips off-times.
  - The effective frequency drops to about 270 kHz, and the HS FET carries almost all the current.

## 2. Losses (Tj iterated; inductor DCR 13.2 mOhm typ, heated)
| case | IC loss | HS conduction | LS conduction | switching + Coss | Qrr | dead time | VCC from VIN | L520 (Cu + core) | RS |
|---|---|---|---|---|---|---|---|---|---|
| 6 A, 25 V | **1.9 W** | 1.22 | 0.03 | 0.16 | 0.18 | 0.09 | 0.06 | **0.56 W** | 0.18 |
| 6 A, 36 V | **2.5 W** | 0.91 | 0.33 | 0.35 | 0.40 | 0.13 | 0.13 | 0.76 W | 0.18 |
| 6 A, 42 V | **2.7 W** | 0.80 | 0.44 | 0.40 | 0.47 | 0.13 | 0.15 | **0.90 W** | 0.18 |
| 7.5 A, 25 V | **2.65 W** | 2.09 | 0.04 | 0.16 | 0.19 | 0.09 | 0.05 | **0.93 W** | 0.28 |
| 7.5 A, 36 V | **3.5 W** | 1.58 | 0.56 | 0.43 | 0.51 | 0.17 | 0.13 | 1.15 W | 0.28 |
| 7.5 A, 42 V | **3.7 W** | 1.39 | 0.75 | 0.49 | 0.59 | 0.17 | 0.15 | **1.30 W** | 0.28 |

**IC loss**
- The breakdown columns are the TI-calculator terms. The IC loss column is the calibrated value, which is 0.05-0.3 W higher.
- High line is the thermal worst case.
- BIAS -> VOUT would save only about 0.1 W at 42 V.

**L520**
- Ripple is 2.05 A peak-to-peak at 42 V and 0.2 A at 25 V.
- Core loss is estimated at about 0.3 W at 42 V and close to 0 at 25 V. Tai-Tech publishes no core-loss curve.
- At the DCR maximum of 16.5 mOhm, add about 25 % to the copper loss: about 1.5 W at 42 V and 7.5 A.
- L520 runs at about 100 C at 42 V and 7.5 A. Its limit is 125 C including self-heating: OK.

## 3. Junction temperature at 45 C ambient
Thermal model:
- A 2D board-spreading model: copper k·t sheet, h = 22 W/m²K for both faces (convection plus radiation).
- Heat sources: U511, L520 and R538 at their planned positions.
- Calibrated on the EVM. The EVM board model gives 34.9 C under the IC, so junction-to-board is 8.9 C/W.

Our board as built:
- Copper fill measured from the board around U511: F 0.88, In1 0.94, In2 0.85, B 0.90.
- Effective k·t is about 0.052 W/K. The EVM is about 0.150 W/K, so ours has about 3x less spreading.
- Junction-to-board is taken as 1.2x the EVM's: 4 layers instead of 6, and small B.Cu pads.

| | 25 V | 36 V | 42 V | RthJA effective |
|---|---|---|---|---|
| 6 A, planned layout | 90 C | 104 C | **110 C** | 24 C/W |
| 7.5 A, planned layout | 109 C | **128 C** | **134 C** | 24 C/W |
| 7.5 A, poor copper (k·t 0.040, junction-to-board 1.3x) | 120 C | | 149 C | |
| 7.5 A, section 4 done (30 x 30 mm solid, EVM-class vias) | | 113 C | **118 C** | 20 C/W |

Copper needed for Tj <= 125 C at 7.5 A and 42 V. The block is solid on all four layers and centred on U511; side length in mm:

| side of the solid block | none | 20 mm | 30 mm | 40 mm | 50 mm |
|---|---|---|---|---|---|
| EVM-class die attach (junction-to-board 1.0x) | 126 | 120 | 118 | 116 | 115 |
| as planned (junction-to-board 1.2x) | 134 | 127 | 125 | 124 | 123 |

**Reading the sweep**
- Via attach is worth about 8 C. A local solid block is worth about 8-10 C.
- Copper beyond about 30 mm on a side barely helps; the board's 1 oz inner layers set the limit.
- Model uncertainty is about ±10-15 C. Treat 7.5 A as "bench-proven or not rated".

## 4. Layout conditions that make 7.5 A true
**Where the heat leaves the IC**
- The HS FET takes 60-80 % of the IC loss: 2.1 of 2.65 W at 25 V.
- With a drain-down die, which is likely but not stated by TI, that heat leaves through the **VIN die pad**.
- So +BATT copper is the main heatsink, then PGND. TI's layout example says the same: "maximize VIN and GND copper areas for heat spreading".

**Required copper and vias**
1. **About 30 x 30 mm (about 900 mm²) of near-solid copper on all four layers** around U511.
   - **In1:** unbroken GND, with no traces or slots under the block.
   - **In2:** unbroken +BATT under the IC. The planned split already puts the IC inside the +BATT region x 162-181.
   - **F.Cu:** poured everywhere: BATT_U511, GND_U511, SW_24 and GND around them. Use narrow splits only.
   - **B.Cu:** large pours.
     - Replace the tiny `BATT_EP_U511_B` (die pad + 0.25 mm) and `GND_EP_U511_B` (pad 30 + 0.4 mm) with a **+BATT pour of at least 15 x 15 mm** under the VIN side.
     - Add a **GND pour of at least 15 x 15 mm** under PGND and the input-cap side.
   - **Move the B.Cu ISNS+/VOUT Kelvin pair** (about 25 mm) out of the block. Run it along the edge or on F.Cu, because it cuts the B.Cu spreader.
2. **Via count (0.3 mm drill, about 1 mm pitch):**
   - Keep the footprint's 6 VIN-pad and 6 PGND-pad vias.
   - Grow `BATT_U511` from 8 to **at least 16** In2/B.Cu +BATT vias within 3 mm of the VIN pins and the die pad.
   - Grow `GND_U511` / pad 30 from 10 + 6 to **at least 20** GND vias.
   - No vias in the SW pad (TI's practice, for EMI).
3. **No other heat source within about 20 mm** of U511, or add its rise.
   - The model assumes the ESC stages are not heating this corner.
   - Board heating from other parts adds directly: every 5 C of extra local board temperature puts 7.5 A out of spec.
4. **Optional margin of 10-20 C:**
   - A gap pad from the U511 top to the lid or a heat spreader: psiJT(max) is 0.8 C/W, so the top is close to Tj.
   - Or about 100 LFM of airflow; TI's EVM spec uses this above 60 V.
5. **Bench acceptance test:**
   - Conditions: 7.5 A, 42 V and 36 V, 45 C chamber, 30 min, the ESCs at their normal duty.
   - Measure the hottest point on the U511 top with IR.
   - Tj ≈ Tcase-max + 0.8 x 3.7 W, about Tcase + 3 C. **Pass if the case is at or below 120 C.**

## 5. F1 and the J510 path at 7.5 A
**Input current at 7.5 A out**
- Pin is about 184-185 W.
- Low line: about 7.4 A at 24.8 V of +BATT, plus about 0.7 A of logic = **about 8.1 A**.
- 36 V: about 5.1 A, plus logic.
- High line (42 V): about 4.4 A.
- 6 A out at low line: about 6.6 A.

**Low-line UVLO**
- A 25 V pack at load gives +BATT of about 24.8 V, which is at or below the UVLO-off threshold: 24.9 V typical, 23.7-26.2 V range.
- So U511 can switch off near 25 V. Realistic low line is about 26 V.
- In dropout, the output is about 24.3 V.

**F1 (10 A, 58 V ATO)**
- A blade fuse used continuously at 45 C allows about 0.8 x 0.94 x 10 A, about 7.5 A.
- **8.1 A does not fit, so use 15 A for 7.5 A continuous.** 10 A stays fine for 6 A continuous.
- Q1 (SQJ459EP) dissipates about 1.5 W at 8.1 A. Its BATT_Q1 pour (5.8 x 4.3 mm, 9 vias) should grow with it.

**J510 path**
- **J510 itself is fine:** the MKDS 1,5 is rated 13.5 A. Its +24V share is 6-7.5 A.
- **The plane is fine:** In2 +24V, about 20 mm wide over about 40 mm of 1 oz: about 1 mOhm, about 0.06 W.
- **J510 pad 1 is the weak spot, confirmed on the board.**
  - +24V reaches pad 1 only through In2 thermal relief: 0.4 mm spokes, 0.3 mm gap. There is no F.Cu or B.Cu +24V copper.
  - Four 0.4 mm, 1 oz spokes are not good for 7.5 A continuous.
  - **Before fab:** give pad 1 a solid zone connection (pad override, or zone connection = solid), and add an F.Cu/B.Cu +24V pour from the R538/C531 vias to J510.
  - Pad 2 (GND) has spokes on F, B and In1, so 12 spokes. Making it solid too is recommended.

## Files
- Datasheet SNVSCD3: https://www.ti.com/lit/ds/symlink/lm70880.pdf (Fig 5-3, Fig 7-7, section 5.4, section 7.4).
- EVM guide SNVU872A: https://www.ti.com/lit/pdf/SNVU872 (Fig 3-11 thermal image, Fig 4-10 stack-up).
- TI quickstart calculator: https://www.ti.com/tool/download/LM70XX0-CALC (LM70XX0_quickstart_calculator_A1.xlsm; sheets "Efficiency Calculations" and "Variable Management").
- Tai-Tech TMPC1265HP datasheet (LCSC C305223): DCR 13.2 mOhm typical, 16.5 mOhm maximum; Irms 10 A at a 40 C rise.
- Model scripts (scratchpad, not in the repo), all under `/tmp/claude-1000/-home-mark-Documents-VE-V3/412ee8fb-27c0-4acd-98aa-e7fcd601bdf3/scratchpad/scr/`:
  - `loss.py`: the TI calculator equations plus the derating check.
  - `plate.py`: the 2D board model.
  - `run.py` and `sweep.py`: the sweeps.
  - `j510.py`: the J510 pad check, run on a copy of the board.
