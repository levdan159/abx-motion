# Buck placement: report (2026-10-24)

## What I changed
- **New script:** `.claude/handoff/bl/buckplace.py <board>`.
  - It moves parts only. Every move uses absolute coordinates, so it is idempotent.
  - It refuses to run while KiCad is open.
  - It checks itself: courtyards against every front-side part, the region, and the pad nets the routes rely on.
- **Pipeline:** `buckplace.py` → `critical.py` → `pours.py`.
- **The real board was not touched.** Work copy (piped from the real board): `/tmp/claude-1000/-home-mark-Documents-VE-V3/412ee8fb-27c0-4acd-98aa-e7fcd601bdf3/scratchpad/buck/work/abx-motion-brushless.kicad_pcb`. The DRC JSON is next to it.
- **Baseline:** the same `critical.py` + `pours.py` run on an unmodified copy: `scratchpad/buck/base/`.

## Placement (TI TPS54560B layout example, IC rotation unchanged)
Each buck has its parts in these spots:

- **Catch diode:** horizontal, directly above the IC.
  - Cathode (SW) above pin 8, beside the inductor's SW pad.
  - Anodes (GND) on the left, next to the GND pads of the 1210 + 100 nF input caps.
  - So the hot loop is VIN cap → pin 2 → pin 8 → cathode → anode → cap GND, about 6 × 7 mm.
  - The SW node is pin 8 + cathode + inductor pad, a single F.Cu pour.
  - Nothing else would fit "between pin 8 and the inductor": L520/L521 cannot move right (D522, U513 and C544 are in the way), and D2 blocks the top-left corner.
- **BOOT cap:** vertical, in the 1.7 mm gap between pin 8 and the inductor. Pad 2 (SW) is level with pin 8.
  - The BOOT trace runs from pin 1 over the top of the IC, between the pins and the diode pads.
- **VIN caps:**
  - The 100 nF cap (C524/C537) sits right at pin 2.
  - One 1210 sits beside it.
  - The bulk 1210s moved to the left, fed by +BATT pours with vias to the In2 +BATT plane.
- **EN and RT:**
  - EN top resistor (0805) left of pin 3; EN bottom resistor beside it.
  - RT resistor right under pin 4.
- **FB and COMP:** one row under pins 4–6: R(RT) | Rfb-top | Rfb-bot | Chf | Rcomp.
  - FB runs straight down from pin 5.
  - COMP leaves pin 6 to the right, then runs down a lane that stays 1 mm from the SW pads.
  - The CZ cap sits under Rcomp.
- **IC moves:** U511 and U512 each moved 2.0 mm straight down, to make room for the diodes. The inductors, output caps and connectors did not move.

| ref | value | old | new |
|---|---|---|---|
| U511 | TPS54560B | (176.00, 118.50) 0° | (176.00, 120.50) 0° |
| D520 | PDS5100H | (178.75, 125.44) 90° | (175.90, 115.27) 180° |
| C528 | BOOT_24 | (178.56, 114.64) 0° | (180.63, 118.29) 270° |
| C524 | 100n VIN | (172.70, 114.65) 0° | (171.40, 119.15) 90° |
| C520 / C522 | VIN 1210 | (170.22 / 166.54, …) | (168.32, 118.60) / (165.00, 117.86) |
| C521 / C523 | VIN bulk | (173.44, 123.27) / (168.76, 123.73) | (164.80, 126.75) 90° / (169.60, 126.20) 180° |
| R520 / R521 | EN_24 | (165.87, 122.78) / (163.84, 119.14) | (171.05, 122.70) 90° / (168.50, 122.40) 180° |
| R522 | RT_24 | (167.45, 127.91) | (174.00, 124.88) 270° |
| R523 / R524 | FB_24 | (188.88, 128.64) / (165.59, 126.65) | (175.60, 124.88) 90° / (177.20, 124.88) 270° |
| C527 / R525 / C526 | COMP/CZ_24 | (174.92, 126.70) / (187.01, 112.40) / (168.84, 114.38) | (178.80, 124.88) / (180.40, 124.88) / (180.60, 127.95), all 270° |
| U512 | TPS54360B | (176.00, 133.50) 0° | (176.00, 135.50) 0° |
| D521 | PDS5100H | (179.17, 140.47) 90° | (175.90, 130.27) 180° |
| C540 | BOOT_12 | (167.60, 131.59) 90° | (180.85, 133.29) 270° |
| C537 / C534 | VIN | (168.84, 136.42) / (170.30, 132.87) | (171.40, 134.15) 90° / (168.40, 133.35) 90° |
| C535 / C536 | VIN bulk | (171.22, 128.54) / (173.30, 138.26) | (164.80, 131.75) 270° / (164.60, 136.50) 90° |
| R526 / R527 | EN_12 | (165.99, 135.80) / (174.90, 141.15) | (171.05, 137.55) 90° / (168.50, 137.05) 180° |
| R528 | RT_12 | (175.04, 143.01) | (174.00, 139.88) 270° |
| R529 / R530 | FB_12 | (182.60, 143.51) / (184.50, 142.68) | (175.60, 139.88) 90° / (177.20, 139.88) 270° |
| C539 / R531 / C538 | COMP/CZ_12 | (183.00, 128.74) / (178.70, 145.53) / (180.86, 133.09) | (178.80, 139.88) / (180.40, 139.88) / (180.60, 142.95), all 270° |

## Routing result (critical.py)
- **All 18 buck connections route; no FAIL or SKIP lines.**
  - Lengths: 0.8–2.8 mm, except BOOT at 6.5–6.7 mm.
  - All on F.Cu, no vias.
- Whole run: `routed 64 failed []`. The baseline had 52 routed and 12 failed.
- **Idempotent:** running all three scripts a second time on the result gives identical tracks, footprints and zones (md5 of each matches).

## DRC (`kicad-cli pcb drc --schematic-parity --refill-zones`)
| | baseline | new |
|---|---|---|
| clearance / shorting_items / tracks_crossing / track_dangling / via_dangling / hole_clearance / courtyards_overlap / copper_edge_clearance / isolated_copper | 0 | **0** |
| schematic parity | 0 | 0 |
| starved_thermal | 8 | **7** |
| lib_footprint_mismatch / silk_overlap / silk_over_copper / silk_edge_clearance | 125 / 199 / 199 / 6 | unchanged |
| unconnected, DRC JSON (KiCad caps this at 499) | 499 | 499 |
| **unconnected, true count** (pcbnew, after zone fill) | **534** | **511** |

- **Buck nets that are now fully connected:** BOOT, EN, RT, FB, COMP, CZ and SW of both bucks.
- **+BATT pads now joined to the plane:** every buck VIN and EN pad, including C523, which was isolated before.
- **Still open on these nets:** only the +24V/+12V Vout sense pads of R523/R529, and J512. Both were open before too.

## Changes to the existing scripts (both stay idempotent)
- **critical.py:**
  - Removed `C528` and `C526` from `MOVE3`. Otherwise they would override buckplace and drop C526 back into the old spot.
  - Updated two comments to match.
- **pours.py, section 5:** rewrote the buck pours for the new spots.
  - Pours rewritten: `BATT_U511`, `BATT_U512`, `SW_24`, `SW_12`, `GND_U511`, `GND_U512`.
  - New +BATT pours, each with In2 vias: `BATT_R520` (R520 + C523), `BATT_C521_C535`, `BATT_C536`, `BATT_R526`.
  - `BATT_D2` now stops at y 112.7 (it was 113.4), clear of the D520 anodes.
  - New F.Cu `GND_EP_U511_F` / `GND_EP_U512_F` (exposed pad + 0.2 mm, plus a strip to pin 7). Without them the new tracks starved the EP thermals.

## Judgement calls / for the owner
- **IC moves:** U511 and U512 each went down 2.0 mm. A diode can only fit above the IC if the IC moves down: D2's courtyard and L520's courtyard leave only 6.6 mm of width there.
- **12 V buck offset:** I placed it 2.00 mm lower rather than 1.95 mm. At 1.95 mm the router's 0.1 mm grid gave a 0.144 mm COMP_12-to-pin-5 clearance error. At 2.00 mm its geometry matches the 24 V buck, which routes clean.
- **Coupling between bucks:** the buck-24 FB/COMP row sits 1.1–4 mm above the buck-12 diode cathode (SW_12). The 1 mm keep-out is met, and the SW_12 pour is kept out of the strip under C526.
- **COMP lane:** COMP runs down a lane 1.0–1.1 mm from the inductor's SW pad. That is the critical.py rule, so it is acceptable but tight.
- **Not routed yet:** the FB top resistors' Vout pads (R523 pad 1 +24V, R529 pad 1 +12V) need a Kelvin sense line from the output caps. Suggestion: route it on B.Cu with a via at the pad, away from the inductors.
- **Stale text:** `critical_report.md` still describes the old C528/C526 swap.
- **Not checked:** silkscreen. The silk counts did not change, but the DRC JSON may be capping them at 199.
