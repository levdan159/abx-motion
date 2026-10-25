# High-current pours: `bl/pours.py` (2026-10-24)

The script ran only on a COPY of the board. The real `abx-motion-brushless.kicad_pcb` was not changed (md5 checked against the baseline copy).

- Work copy, with the .kicad_pro beside it: `/tmp/claude-1000/-home-mark-Documents-VE-V3/412ee8fb-27c0-4acd-98aa-e7fcd601bdf3/scratchpad/pours/abx-motion-brushless.kicad_pcb`
- Run: `~/.cache/mark-mods/kicad-mcp-big-venv/bin/python .claude/handoff/bl/pours.py <board.kicad_pcb>`. Close KiCad first (pgrep guard). Run `planes.py` before this script, never after it, because planes.py deletes every In2 zone.
- Re-runnable:
  - It deletes the zones named `PWR_*` and the vias in group `PWR_VIAS`. As a fallback it also deletes free 0.3 mm-drill vias inside old PWR_ outlines that are on the same net.
  - It then rebuilds everything, refills all zones and saves.
  - Running it three times in a row gave identical geometry (same hash of via positions and zone outlines).
- Zones and vias are **locked**. The vias are in one group: in the GUI, double-click the group to edit inside it.
- Every PWR_ zone uses priority 10 (In2 finger: 3), FULL pad connection, 0.25 mm clearance, 0.2 mm min width and always-remove-islands. Every via is 0.6 / 0.3 mm through.

## What it adds: 61 zones, 549 vias
ESC1 is written in ESC1 coordinates. ESC2 is the same copper rotated 180 deg about (140,107), like the placement.

| Group | Zones | Vias |
|---|---|---|
| Phase (x6) | F.Cu: J301/J401 pole + high-FET source pins + low-FET drain pad (`PWR_Mx_PH_y_F`). B.Cu copy of the part above the FET row (`_B`) | **40 per phase** (240), F<->B, in a block between the FETs and the terminal |
| VBUS at the stage | F.Cu over each high drain + its two 1210 bus caps (x6). C327/C427 (x2). ESC1 bulk C328/C329 is merged with phase C's zone and has a strip down to the bulks. ESC2 bulk C428/C429 + D401 | 6-7 per high FET in the drain/cap gap. 24-30 per bulk pair. 1 per C327/C427. All go to In2 VBUS |
| In2 finger `PWR_In2_VBUS_Q405` | In2 VBUS x161.5-166.4, y141.6-149.6 (priority 3, cuts +BATT locally). Q405's drain sits past the x=162 VBUS/+BATT split | - |
| Low source -> shunt (x6) | F.Cu `PWR_Mx_SPy`: Q low source pins -> R x07-x09 pad 1 | none (keeps the Kelvin sense area clear) |
| Shunt / bus-cap GND (x6) | F.Cu, solid: shunt pad 2 + both bus-cap GND pads | 5-9 each to In1, pitch 1.3 mm |
| Breaker | F.Cu + B.Cu VBUS at Q802/D301 (x168.5-188.8, y<67.3). F.Cu BUS_SRC between Q801 and Q802 sources. F.Cu + B.Cu BUS_SNS (Q801 drain + R801 pad 2). F.Cu VBAT_IN at R801 pad 1 / F1 pad 1. F.Cu VBAT_IN at J1. **B.Cu VBAT_IN** J1 -> under R801/F1 (x178-213, y86-105) | VBUS 40. BUS_SNS 8 (to B). VBAT_IN 36 at R801 + 30 at J1 |
| Logic branch | F.Cu V_FUSED (F1 pad 2 -> Q1 drain, ~154 mm² for Q1's ~1.1 W). +BATT at the Q1 source pins. +BATT at D2 | 9 + 6 to In2 +BATT |
| Bucks | SW_24 (U511.8 / D520 K / L520.1, ~72 mm²). SW_12 (U512.8 / D521 K / L521.1, ~78 mm²). +BATT input-cap pours for U511 (C520-C524, C535) and U512 (C534, C536, C537). Solid GND for EP + pin 7 + Cin GND + catch-diode anodes (U512's also takes C538 GND). B.Cu GND under the U1/U511/U512 EPs + F.Cu under U1 EP | +BATT 8 + 4. GND 3 + 4 |
| +24V / +12V | +24V pours on L520.2, C529/C531, C530+C532, C533. +12V F.Cu L521.2 + C541/C542/C543. **B.Cu +12V strip** -> J511 pin 1 | +24V 19 to In2. +12V 6 to the B strip |

No signal tracks were added.

## Keep-outs for the router
Vias stay out of:
- 2 mm around every gate-drive pad (GHx/GLx/*_G);
- 1.5 mm around the breaker gate / CSP, Q1_GATE, SENS and SPx pads;
- 1 mm around the buck EN/RT/FB/COMP/CZ/BOOT pads.

No zone reaches the DRVs or the gate resistors. Every zone refills around tracks, so gate and sense tracks win.

Each low-FET gate pin (top right of the FET) has an open F.Cu channel at y≈65 to its right. Each high-FET gate pin sits inside the phase-node copper, which is correct: GH is referenced to the phase node. The router should take GH out with a short stub plus a via next to the pin, then run on B.Cu (B.Cu under the FET row stays GND).

## DRC (`kicad-cli pcb drc --schematic-parity --refill-zones`)
| Type | Before | After |
|---|---|---|
| silk_overlap | 199 | 199 |
| silk_over_copper | 199 | 199 |
| lib_footprint_mismatch | 125 | 125 |
| lib_footprint_issues | 9 | 9 |
| starved_thermal | 48 | **6** |
| silk_edge_clearance | 6 | 6 |
| isolated_copper | 5 | **0** |
| clearance / short / hole / zones_intersect | 0 | 0 |
| parity | 0 | 0 |
| unconnected (the JSON list is capped at 499 both times) | 499 | 499 |
| ratsnest edges (pcbnew `GetUnconnectedCount`) | 703 | **595** |

- The 6 starved_thermal left are not power: U801 pad 6, J201 A1/A12/B1/B12, U513 pad 15.
- The 5 isolated_copper were In2 +BATT islands. The +BATT vias now tie them in.

Renders (custom per-net fill plots) are in the work dir: `v_F_esc1.png`, `v_F_esc2.png`, `v_F_aux.png`, `v_B.png`, `v_In2.png`.

## Judgement calls
1. **No F.Cu path exists from J1 to R801.** C525 and R801's BUS_SNS pad 2 block it. The 60 A battery path is therefore B.Cu (2 oz, new VBAT_IN pour) plus In2 VBAT_IN, with 66 vias at the two ends. Under Q801, In2 VBAT_IN is mostly removed by Q801's own thermal vias, so B.Cu does the real work.
2. **B.Cu phase copper covers only the area above the FET row.** Under the FETs, B.Cu stays GND, so gate/sense routing on B.Cu stays free.
3. **Phase via blocks use a 1.0 mm pitch.** In2 VBUS and In1 GND become solid holes there. This is acceptable because that region (between the FETs and the terminal) is a dead end for both planes. The GND shunt vias use a 1.3 mm pitch so that In2 VBUS still flows between them.
4. **In2 VBUS finger under Q405.** Without it, ESC2 phase C's high FET (x 161-166) has no VBUS via at all: In2 is +BATT past x=162.
5. **+12V has no In2 plane.** It gets a 2.2 mm B.Cu strip to J511 (3 A), routed under U513's area but clear of its EP vias.
6. **The ESC2 copy of phase A's upper zone has a corner notch** so it does not wrap TP_5V1 / TP_GND1.
7. **Overlapping same-net pours are merged automatically.** Different-net pours on the same layer are checked for overlap (warning printed; none found).

## Open issues / for the owner
- **In2 planes use thermal-relief pad connection (planes.py).** J1's BAT+ pads and Q802's thermal vias reach In2 through spokes. B.Cu (FULL) and the new vias carry the current, but consider `ZONE_CONNECTION_FULL` for the In2 power planes.
- **VBUS vias per high FET: 6-7 only** (drain/cap gap). For more, use via-in-pad in the drain pads (filled/capped) or move the 1210 caps.
- **Net classes miss the breaker nets.** VBAT_IN and /Bus_Breaker/BUS_SRC/BUS_SNS are not in a Power_HV pattern (Default, 0.15 mm). The zones set 0.25 mm locally, but tracks on those nets would not. VBAT_IN is in the brief's Power_HV list but not in the .kicad_pro patterns.
- **Placement nits:**
  - C538 (CZ_12) sits between U512 pin 8 and L521, so the SW_12 copper wraps it. Moving C538 would tighten SW_12.
  - C535 (U512 input cap) is far from pin 2.
  - U512's +BATT pour got only 4 vias, because of the EN/RT keep-outs.
- **J301/J401 bodies sit on the phase via blocks.** The vias should be tented, which is the default.
- **ESP32 U3 antenna is next to phase C's upper zone** (x>=112). There was already GND pour there before, so this is no worse. Check the module's keep-out drawing.
