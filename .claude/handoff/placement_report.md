# Placement of the staged parts (2026-10-25)

Board `abx-motion-brushless`, branch `v1.0-bl-wip`. Nothing committed. KiCad was closed for every write.
Backup of the real board before this: `bak/pre_placement/` (board, .kicad_pro, HANDOFF, and `bl/` buckplace, critical,
fill, pours as they were).

## Result (real board = the tested copy, checked item by item: footprints, tracks, zones identical)
| check | before | after |
|---|---|---|
| parts off-board (x > 215) | 80 | **0** |
| DRC parity | 0 | 0 |
| clearance / short / courtyard / hole / hole_to_hole / mask bridge | 0 | **0** |
| track / via dangling | 0 | 0 |
| starved_thermal | 9 | 15 (+6, see below) |
| silk_edge_clearance | 3 | 4 (+ J704 reference text) |
| lib_footprint_mismatch / silk overlap / silk over copper | 35 / 199 / 199 | unchanged |
| unconnected (DRC = pcbnew ratsnest count, below the 499 cap) | 301 | **219** |
| critical.py | | 67/67 routed (U511 block now on the board) |
| pours.py | 49 zones, 512 vias | 61 zones, 538 vias, no overlap warning |
| groups | critical_routes 409, PWR_VIAS 512, cleanup_routes 622 | 488, 538, 582 |
| KRT check_floorplan --intent | | **0 errors**, 3 warnings (2 zone-overlap notes, H4 pins_to_edge, old) |
| KRT check_assembly --baseline | | **buildable, blocking 0, new-vs-baseline 0** |
| idempotency | | 2nd full pass = identical footprints, tracks, zones |

New starved thermals: C521, C550, C551 (the LM70880 block, already listed in `lm70880_report.md`), C909 GND pad,
U1 pin 7 and U901 pin 7. The two pin-7 entries are the GND pour's spoke count only: the pins sit on the new EP strip
zones (fill checked, solid). C909 gets its GND via when routed.

## Pipeline (run on the real board, in this order)
`bl/newplace.py <board>` (new) -> `buckplace.py` -> `critical.py` -> `pours.py` -> `fill.py`.
Helper: `bl/place_tools/pipeline.sh <board> <logdir> [--usb-top]` runs the five steps; `drc.sh` diffs DRC against the
pre-placement report (paths inside point at this session's scratchpad: edit before reuse).

`newplace.py` (buckplace style: absolute poses, re-runnable, refuses to run with KiCad open):
- copper ending on a pad that moves is deleted (16), GND pour stitches / stubs of `cleanup_routes` or no group under a
  new pad or inside a new courtyard are deleted (26), then what that left dangling is trimmed (16). Never
  `critical_routes` / `PWR_VIAS`; any other foreign copper near a new pad would be printed as COPPER CONFLICT (none).
- checks: courtyards (strict: touching counts), board outline, the pad nets of both TPS54360B blocks.
- `--usb-top` = the USB-C proposal below (copy only).

`pours.py` edit (one block): U901 joins U1 in the exposed-pad section, and both TPS54360B get an F.Cu strip from the EP
to GND pin 7 (merged zones `PWR_GND_EP_U1_F+GND_P7_U1_F`, `..._U901_...`, plus `PWR_GND_EP_U901_B`). Without it
U901's 15 thermal-via pads were starved. No other copper was added: the U1/U901 SW / +BATT / GND hot-loop pours and
their small-signal routes are NOT made (see "next").

## What went where, and why
**U1, 5 V TPS54360B** at (79.75, 92.0) rot 0, left logic column just above the old U1 spot (that spot is taken by U2,
C9/C10, R2/R3/C1, the power LEDs; they were not moved). **U901, +5V_AUX** at (88.0, 135.0) rot 180, below the cluster.
- Layout per TI SNVSB93 sec. 10.1 + fig. 52, read from the datasheet: catch diode + inductor at SW, input cap loop
  VIN -> diode anode short, RT and UVLO resistors left, comp network + FB divider under COMP/FB, topside GND.
- Offsets copied from the U512 TPS54360B arrangement `buckplace.py` used on 2026-10-24 (same chip, critical.py routed it
  18/18, pours.py had its pours): diode above the IC (cathode over pin 8), CBOOT between pin 8 and L, 100 nF at pin 2,
  4.7 uF beside it and a second one further left, EN pair left of pin 3, RT / FB / Chf / Rcomp row under pins 4-6, CZ
  under Rcomp, L right of CBOOT, the two 47 uF right of L. The offsets were kept on purpose: the old U512 sections of
  `critical.py` and `pours.py` (in `bak/pre_esp_removal/bl/`) can be ported to U1 / U901 as a translation.
- U901 is turned 180 deg so its input faces the +BATT trunk (x 92-105) and its output faces J511.
- The block's parts that were already on the board (C2-C4, C6-C8, R4, R5) moved with it; their old copper was deleted.

**+5V_AUX chain**: C908 at the buck output, U902 TPS25200 (IN towards the Cout, OUT towards the edge), C909 in, C910 out,
R905 ILIM at pin 2, R906 FAULT pull-up, D901 SMAJ5.0A beside J511, **J511 on the left edge at (50.1, 135.5) rot 270**
(wire entry out, pin 1 +5V_AUX on top; same orientation as J205).

**Breaker sequencer** U802 LM339 + 18 parts in the free strip right of U801 (x 202-213, y 61-85), above the VBAT_IN pour
(y > 85.8). C811 sits 3.5 mm from VCC pin 3 (the 3rd pin of the row: no closer spot outside the package).
**Precharge**: R830 (169.5, 94.25) / R831 (173.5, 94.25), both vertical, directly below R803, so the string reads
R803 -> R830 -> R831 -> R804 (PRE_M at the top, PRE_M2 joined at the bottom). Room is left round them for a PRE_M2 /
PRE_M3 copper pour (not made).

**IMU U711** (152.0, 116.25) rot 90 with C726/C727 at its supply pins and R713/R714: right of U701 between the crystal
area and J304/J404. 19 mm from the I2C pins, 24 mm from the board centroid (U701 itself sits on it and its ring of
decaps fills the space), 26-33 mm from the ESC2 shunts/FETs, 28 mm from L520, 40+ mm from L1/L901. Nothing nearer
the centroid is free of courtyards and routed copper.

**VBUS divider R711/R712** (107.25, 108.0) / (108.75, 107.25), right of LOGO1: 13.6 mm from PA9. The pin side of U701
(U705, C708, C721, R710) has no room for the pair.

**I/O header J704** on the top edge at (97.0, 50.9) rot 0 (pins x 97-111), ESD U708-U710 right behind it (y 56),
the six 100 R series resistors behind those (MCU side, y 59.8), F701 + C728 at pin 1. Top edge chosen: free, nearest
free edge stretch to the U701 left-side pins (PB13/PD11/PD15), away from the bucks' SW nodes.

**USB-C / CAN: NOT moved on the real board (owner decision).** No enclosure / mechanical data exists for the board, so
the connectors' edges are your call.
- Proposal, placed and checked on a copy only (`newplace.py --usb-top`): J201 to the top edge at (84.0, 52.5) rot 180
  (opening up) with U201, R201, R202, F2, D202 behind it. PA11/12 distance about 87 -> 69 mm, and the pair no longer
  crosses the left column with the two 5 V bucks. Copy result: 0 copper / courtyard errors, parity 0, unconnected 230
  (the old USB copper is ripped), floorplan 0 errors, buildable. Render `png_placement/placement_top_usbtop.png`.
- CAN J205/J204/R219: no edge is much nearer U704 (best gain about 12 mm). CAN at <= 1 Mbit/s does not care about
  80 mm of differential pair, so I propose to leave it.

## How the poses were found (deviation from the brief)
`place_simple.py` was NOT used for the final poses. It sees courtyards and intent keep-out rectangles, not tracks or
vias, and this board is already routed (2800 segments, 985 vias, locked pours). Its output would land pads on routed
copper (the 2026-10-24 p1 run worked around that with hundreds of keep-out rectangles). Instead, a small copper-aware
search (`bl/place_tools/`):
- `engine.py`: rasters of foreign-net copper (F/B) + courtyards; exact courtyard check; GND stitches count as removable;
- `tsearch.py`: anchor search for the two TPS54360B templates;
- `greedy.py` + `spec.py`: one part at a time, cheapest legal pose by pad-to-partner distance, inside a window per
  function (decaps at their pins, ESD at the header pins, series R behind the ESD, divider pair, ...).
Its poses are written as absolute coordinates into `newplace.py`. The KRT graders were then run as asked:
`check_floorplan --intent` (0 errors) and `check_assembly --baseline` (buildable), outputs in `bl/place_tools/`.

**Intent** (hand-written, requirements, not emitted from the board): `.claude/handoff/placement_intent.json`
(the `--usb-top` copy: `placement_intent_usbtop.json`; generator `bl/place_tools/mkintent.py`).
- 7 blocks with zones (one per function).
- 5 keep-outs over the power stages / bucks for the IMU group.
- 20 proximity rows: decaps at pins, ESD at its header pins, TVS at J511, precharge string, U802 near U801,
  IMU near the I2C pins, divider near PA9.
- keep_away: U1_SW / U901_SW vs OSC / I2C1 / USB 3 mm. Measured: 28.6 mm and 42.2 mm.
- edge connectors: J511 W, J704 N, J201 W (N in the copy), J205 W.

## Renders (`.claude/handoff/png_placement/`)
`placement_top.png`, `placement_bottom.png` (real board, kicad-cli 3D), `placement_top_usbtop.png` (copy with the USB
proposal), `placement_moves.png` (KRT placement view: courtyards, moves from the staging area).

## Plane mapping (report only; nothing built)
Data: `list_nets --power` on the placed board; currents from the design reports (no new datasheet lookups needed).
- **In1 = GND: keep.** GND has 359 pads (241 F.Cu SMD), and In1 is the reference for the F.Cu signal layer. It also
  carries the GND return of both new 5 V bucks under their hot loops.
- **In2 left column (x 45.5-100) is the `+3V3` plane: it no longer fits.** +3V3 now has 16 pads spread over x 58-210:
  U2, R8, J102, R906 left; F701 top; R812 + R824-R828 at the breaker; R510 / R533 / R537 at the brake driver.
  Total about 0.3 A. That column now holds both TPS54360B inputs (+BATT: C2/C3/C4/R12, C901-C903/R907).
  - Recommendation: make In2 there a **+BATT island** under the two bucks' input caps. Feed it from the existing F.Cu
    +BATT trunk; the bucks draw under about 1 A at 25 V.
  - Run +3V3 as traces.
- **+3V3_ESC island under the STM32** (the known idea): 57 pads, x 107-163, y 77-137; it is the most plane-worthy
  rail without a plane.
  - Proposed: carve about x 112-150, y 95-120 out of In2 VBUS.
  - Trade-off for the owner: the VBUS In2 width between ESC1 and ESC2 at that row drops from about 62 mm to about
    24 mm (x 100-112 + 150-162). ESC2's bus current (30 A peak, regen too) then leans on that narrower inner copper plus
    the bulk-cap pours.
  - Check that cross-section before building it.
- VBUS, VBAT_IN, +BATT (right), +24V: In2 regions unchanged and still matching their parts. U511 now sits inside the
  +BATT / +24V regions as planned.
- +5V (20 pads, x 56-205) and +5V_AUX (4 pads, J511 corner): traces.

## Owner decisions / next
1. USB-C to the top edge (`--usb-top`): yes/no. CAN stays unless you want it moved.
2. Port the old U512 hot-loop pours (SW, GND, +BATT) and the FB/COMP/CZ/RT/EN/BOOT routes to U1 and U901.
   - Sources: `bak/pre_esp_removal/bl/pours.py` section 5 and `critical.py` `bucks()`, with the offsets of this
     placement.
   - D902 (about 1.3 W) needs its copper here: about 60 mm2 F.Cu like the old SW_12 pour, plus GND on the anode with
     In1 vias. There is room below D902.
   - The same applies to D3.
3. Precharge PRE_M2 / PRE_M3 heat copper round R830/R831, if wanted. A single 0.18 s pulse is absorbed by the film,
   not the copper.
4. In2 re-plan as above (`planes.py` owns In2; it hard-codes the real board path).
5. Then the routing of the 219 airwires (KRT leftovers / Freerouting + cleanup as before).
6. Silk: J704 reference over the edge; general silk pass after routing.
7. `bak/pos_snapshot.json` is still stale (posdiff needs the live editor): refresh with `bl/posdiff.py snap` once
   KiCad is open.
