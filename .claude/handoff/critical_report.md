# Critical routing: report (2026-10-24)

Script: `.claude/handoff/bl/critical.py <board.kicad_pcb>`. It refuses to run while KiCad is open and edits only the file you pass it.
The real board was not touched. Work copy, already routed: `/tmp/claude-1000/-home-mark-Documents-VE-V3/412ee8fb-27c0-4acd-98aa-e7fcd601bdf3/scratchpad/crit/work.kicad_pcb` (+ `.kicad_pro`).
The DRC reports are in the same folder: `base_drc.json` (before) and `final_drc.json` (after).

## Re-runs
- Every track and via the script makes goes into the PCB group `critical_routes`. A re-run deletes that group's tracks and vias first, then routes again.
- Tested: two runs back to back give identical copper (439 unique items).
- All placement changes use absolute coordinates, so a re-run puts each part in the same spot.

## Result
| | before | after |
|---|---|---|
| clearance / short / crossing / dangling / hole / courtyard / edge errors | 0 | **0** |
| silk_overlap / silk_over_copper | 199 / 199 | 199 / 199 |
| lib_footprint_mismatch / lib_footprint_issues | 125 / 9 | 125 / 9 |
| starved_thermal | 48 | **47** |
| silk_edge_clearance / isolated_copper | 6 / 5 | 6 / 5 |
| schematic parity | 0 | 0 |
| unconnected, DRC JSON (KiCad caps this list at 499) | 499 | 499 |
| **unconnected, true count** (pcbnew connectivity after zone fill) | **703** | **636** (67 connections routed) |

The DRC JSON's unconnected list stops at 499, so it cannot show a drop. Use the true count instead: `scratchpad/crit/conn.py <board>`.

Copper added:
- 275 F.Cu segments, about 437 mm.
- 125 B.Cu segments, about 386 mm.
- 42 vias: 26 of 0.6/0.3 mm and 16 of 0.5/0.25 mm.
- Nothing on In1 or In2.
- No zones were added.

## What was routed
**ESC1, then ESC2 as a point reflection about (140,107):**
- The script maps nets 3xx to 4xx. 56 track ends that sit in ESC1 pads were checked against the matching ESC2 pads: 0 mismatches.
- ESC2 is a clean DRC. Each ESC adds 27 connections.

1. **Gate drive, per phase:**
   - **GHx → R:** 0.2 mm inside the DRV fan.
   - **GHx_G + SHx (B.Cu pair):**
     - GHx_G runs from a via at the resistor to a via just above the high FET's pin 4, then a 0.4 mm stub to the pin.
     - The SHx Kelvin trace runs beside it on B.Cu: from a via at the DRV fan to a via in the phase gap beside source pin 3, then a stub to the pin.
     - The gate track follows the SH trace (gate-loop "hug" cost).
   - **GLx:**
     - Fan, then via, then B.Cu, then a via under the gate resistor, which now sits in the channel beside the low FET.
     - The resistor's pad 2 connects to pin 4 with a 0.9 mm stub.
     - GLC stays entirely on F.Cu: channel C|B, no vias.
   - **Widths:**
     - Gate nets are 0.4 mm.
     - In the 0.5 mm-pitch DRV fan, every track is 0.2 mm (3–5 mm long).
     - GHx is 0.2 mm all the way to its resistor, because the lanes are only 0.5 mm apart.
2. **Shunt Kelvin pairs SPx/SNx:**
   - 0.25 mm tracks.
   - They start from lead-ins inside each shunt's pad inner edges and meet 0.9 mm apart on the shunt centre line.
   - The pair runs together to DRV pins 9/10, 12/11 and 19/20.
   - SNB hops the SPB lane once, with 2 GND vias. This crossing can't be avoided: SP is on the left at the pins and on the right at the shunt.
3. **DRV local nets:**
   - VM pins 4/5 go to a VBUS via (to In2) and to C320.
   - VCP goes to C317; C317's VBUS pad gets its own via.
   - CPH/CPL go to C316. DVDD goes to C318. VREF goes to C319.
   - The GND ends stop at their pads.
   - **The DRV8323S has no VGLS or AVDD pins,** so there was nothing to route for those.
4. **STM32:**
   - OSC_IN / OSC_OUT: about 1–3 mm from the pins to Y701, and about 1 mm from the crystal to each load cap.
   - VCAP1 → C711.
   - VCAP2 → C712: routed inside the pin row, so GND pin 74 and +3V3 pin 75 keep their exits.
   - NRST → C715: one B.Cu hop (2 vias), because the crystal lines are in the way.
5. **Aux bucks, partly:**
   - BOOT_24.
   - EN_24 (R521 ↔ R520 only).
   - RT_24: 10.3 mm, runs between C521 and C523.
   - EN_12: both branches, about 10 mm each.
   - FB_12 (R529 ↔ R530 only).

## Placement changes (needed for the escapes; ESC2 mirrors ESC1 except where noted)
- **Low-side gate resistors moved into the channel beside each low FET's gate:**
  - R311 to (166.85, 66.0).
  - R313 to (149.0, 66.0).
  - R315 to (131.0, 66.0).
  - All at 90°.
  - ESC2: R411 sits at (113.18, 148.0), not the exact reflection, because D401 is in the way.
- **High-side gate resistors:**
  - R310 to (149.0, 86.25) at 0°.
  - R312 to (141.0, 79.6) at 90°.
  - R314 to (139.0, 79.6) at 90°.
- **DRV caps re-stacked on the DRV's right side:**
  - C320 to (145.5, 87.1) at 0°, beside VM.
  - C317 to (145.9, 88.75) at 0°.
  - C316 to (144.6, 90.7) at 180°.
  - C320 used to sit over the top-side gate pins 14–17 and trapped them.
- **Sense/hall passives moved out of the gate-escape area:**
  - ESC1: C331, C341, C342, R316, R318, R319, R325 and R326 moved right of J703 (x 163–166).
  - ESC2: the same parts moved to x 154–160, y 124–132. The two ESCs differ in that area.
  - They are not routed yet. They all sit closer to J304/J404 now.
- **STM32 parts:**
  - C714 to (140.9, 104.45), above the crystal's OSC_OUT pad.
  - C713 to (143.65, 107.95), right of the OSC_IN pad.
  - C701 takes C713's old spot.
  - C712 (VCAP2) goes into U701's corner notch at (122.0, 114.95) at 270°.
- **Buck:** (superseded by `buckplace.py`, see `buckplace_report.md`) C528 (the BOOT_24 cap) swapped places with C526, so its SW pad now sits next to U511 pin 8.

## Not routed, and why
- **FB_24, COMP_24, CZ_24, FB_12 (pin 5 branch), COMP_12, CZ_12:** placement problem.
  - The FB divider tops (R523, R529/R530) and the compensation parts (R525, C539, R531/C538) sit 9–24 mm from U511/U512 pins 5/6.
  - The only paths pass under or beside the SW copper (L520/L521 pads, the D520/D521 cathodes, pin 8).
  - The script only routes these when it finds a path under 8 mm, 1 mm clear of SW, and off other parts' bodies. None exists.
  - Fix: move each buck's catch diode to the SW side (between pin 8 and the inductor), then cluster FB/COMP/CZ in the space this frees below pins 5/6. Then re-run the script; these nets are already in it.
- **BOOT_12:** C540 sits 6 mm away on the VIN side. Its SW pad cannot reach SW_12.
  - There is no room for it next to U512 pin 8 without moving D520 or C538. D520 is 0.04 mm too close for a 0603 above U512.
- **RT_12 and EN_24 (pin 3 branch):**
  - The only paths run under the 1210 input caps or starve their GND pads, so the script skips them.
  - Move R522/R528 and R520/R521 next to pins 3/4.

## Things to know
- **SNx is net GND in the schematic.** The F.Cu GND pour floods onto the SN Kelvin tracks, so they are not true Kelvin traces. For a real Kelvin return, add a net-tie per shunt (SNA/SNB/SNC as their own nets).
- **The SH via sits in the phase gap and joins the phase pour** (same net). The sense point is still source pin 3.
- **The high-side gate via** (about 1.3 mm above pin 4) sits inside J301/J401's courtyard: under the terminal block body, tented. Check that this is acceptable.
- **B.Cu runs stay clear of power pads:** they avoid ±0.6 mm round the FET, shunt and bus-cap pads, and use the phase gaps and channels instead.
  - The power-zone agent should keep its via arrays off those B.Cu tracks; DRC will flag a clash.
  - B.Cu is now cut by 9 tracks per ESC between the DRV and the FET row. In1 stays the unbroken GND plane.
- **New vias:** 20 per ESC plus 2 for NRST (42 total).
  - FET side: 8 (3 GH, 3 SH, 2 GL).
  - DRV side: 5 fan vias and 3 GH resistor vias.
  - Also 2 VBUS and 2 SNB.
- **Visual check:** the per-layer PDFs refilled with `--check-zones` (`scratchpad/crit/pdfs/`) and my pad plots show:
  - ESC1/ESC2 B.Cu mirror each other.
  - No pour islands were created: isolated_copper is unchanged.
