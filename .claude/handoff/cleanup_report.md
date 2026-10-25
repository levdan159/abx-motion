# cleanup.py report (2026-10-24)

`bl/cleanup.py <board> [--rip-pour-crossers]`: stage 4, run after `autoroute.py import` with KiCad closed.
It touches only unlocked (Freerouting) tracks and vias, plus the copper it adds, which it puts in the group
`cleanup_routes`. A re-run deletes that group and builds it again.
Proven on scratch copies only; the real board is unchanged (byte-identical).
- Default run: `/tmp/claude-1000/-home-mark-Documents-VE-V3/412ee8fb-27c0-4acd-98aa-e7fcd601bdf3/scratchpad/clean/varD/abx-motion-brushless.kicad_pcb`, ~12 min.
- `--rip-pour-crossers` run: `/tmp/claude-1000/-home-mark-Documents-VE-V3/412ee8fb-27c0-4acd-98aa-e7fcd601bdf3/scratchpad/clean/varR/abx-motion-brushless.kicad_pcb`, ~19 min.

## DRC (kicad-cli, --schematic-parity --refill-zones)
| type | before | after (default) | after (--rip-pour-crossers) |
|---|---|---|---|
| clearance | 6 | 0 | 0 |
| shorting_items | 1 | 0 | 0 |
| track_width | 18 | 0 | 0 |
| tracks_crossing / track_dangling / via_dangling | 0 | 0 | 0 |
| hole_clearance / courtyards_overlap / copper_edge_clearance / isolated_copper | 0 | 0 | 0 |
| starved_thermal | 60 | 10 | 10 |
| silk_overlap / silk_over_copper / silk_edge_clearance | 199 / 199 / 6 | same | same |
| lib_footprint_mismatch | 125 | 125 | 125 |
| schematic parity | 0 | 0 | 0 |
| **unrouted** (BuildConnectivity after a fill, GetUnconnectedCount(True)) | **195** | **66** | **79** |

Integrity:
- Locked tracks/vias (995), every footprint position/rotation and every zone are identical to the input.
- Re-run on its own output: the track/via set is identical (5878 items default, 5429 with the flag).
- Silk and lib warnings are the old noise; nothing was done to them.

## What the script did (default run)
- **S0, autorouted copper only:**
  - Exact clearance check of all 4196 unlocked items, using KiCad's own shapes and clearances (pad, footprint and net class, holes 0.25, edge 0.3).
  - It ripped the 7 violators: BRK_VREF / BRK_PMODE / BRK_VCP at U513 (U513 footprint clearance 0.2), and CAN_H over the LOGO1 copper.
  - Of the 18 neck-downs, 13 were widened in place (to the class width or 0.15). 5 could not be widened and were ripped: M1_HALL2, U602_ILIM x2, M1_TEMP_MOT x2.
  - Then dangling unlocked branches were removed back to a pad or junction: 53 items (geometric pass, plus KiCad's own dangling verdicts until there were none).
- **Plane fanout:** 112 stub + via units, all into the plane (each via is checked to reach the In1/In2 zone after a refill):
  - GND -> In1, 75. Via 0.6/0.3, stub 0.3, else 0.2.
  - +3V3 -> In2, 33. Via 0.8/0.4, else 0.6/0.3; stub 0.5, then 0.3, then 0.2.
  - VBAT_IN, 4 and VBUS, 1. Via 0.8/0.4.
- **Starved thermals:**
  - 42 GND pads got a second connection, a stub + via to In1. KiCad counts the track as a spoke, so 60 went down to 10.
  - 6 stitch vias went into GND pour islands that had no via or PTH.
- **Routes:** 35 connections, on a 2-layer A* router (0.05 mm grid, 45-degree moves, string-pulled), short ones first:
  - CAN_H: 0.2 mm, 4 vias, off the logo.
  - Rerouted at U513: BRK_PMODE and BRK_VCP (0.2, 2 vias each).
  - VM_BRK: 5 routes (1.5 / 1.5 / 1.5 / 1.0 / 0.6 mm).
  - BRK_OUT1 x2 and BRK_OUT2 (1.5 / 0.6 mm).
  - +24V x2 (1.5), +BATT x8 (1.0), +3V3 x4 (0.5 / 0.3).
  - Phase-sense taps PH_B / PH_C (0.3), U602_ILIM, 6 GND hops.
  - Total added: 183 vias and 605 track segments.
- **Obstacles respected:**
  - Other nets' copper, holes and the edge.
  - Rule areas (the U3 antenna keepout).
  - Other nets' PWR_* pour outlines: no new copper or vias inside them.
  - No via in another footprint's courtyard, and no via-in-pad (0.1 mm gap).
  - A DRC pass removes any added unit that shows up in an error or creates a new starved thermal or island. The router then retries it with +0.03 mm margin.

## Key finding: Freerouting routed through the high-current pours
Freerouting saw the pours as planes and routed through them.
- 347 autorouted items sit inside other nets' PWR_* outlines.
  - 225 of them are in the motor phase pours: hall, BRAKEx_EN, ESTOP_SENSE, +3V3_ESC, +5V, BUS_* and part of the GHx_G nets.
  - Also hit: the GND shunt pours, the SPA/SPB shunt nodes, BRK_VBUS, BUS_SRC and 12V_B.
- 17 PWR_ pours are cut into islands: every motor phase F pour, SPA/SPB, BUS_SRC (the back-to-back FET common source), 12V_B and M2 PH_B/PH_C B.
- DRC cannot see this: the fill clears around the tracks.

An early version of the router "fixed" those islands with 0.2-0.3 mm tracks: a 0.2 mm track between the Q801/Q802 sources, and 0.3 mm tracks on the shunt node. That is electrically wrong.
- The script now never bridges two islands of a PWR_ pour with a track. They are listed below as "pour split".
- `--rip-pour-crossers` rips the 201 autorouted items that cross a split pour (30 nets), plus 379 items of their dangling chains, then reroutes them outside the pours.
  - Result: **all 17 pours whole**, DRC equally clean.
  - Unrouted 79 instead of 66: more of the dense STM32/DRV signals left for hand work.
- **Recommended: run with `--rip-pour-crossers`.** It costs 13 more hand routes, but halls and enable lines no longer cross 30 A switching nodes. Owner's call.

## Remaining connections (default run, 66)
"no path" means the A* found no legal route inside the window at any allowed width; the window size is given.
- Most of the misses are in the U701 / U302 / U402 block, where the autorouted copper leaves no channel.
- Needs hand work or a second Freerouting pass with the pours fixed.
- Coordinates are in mm.

| # | net | from | to | why (router) |
|---|---|---|---|---|
| 1 | `+12V` | zone PWR_12V_B B.Cu, | zone PWR_12V_F F.Cu, | PWR_ pour split into islands (by autorouted tracks): needs copper, not a track |
| 2 | `+3V3` | C10.1 (71.1, 117.7) | track F.Cu, (78.6, 118.0) | no legal plane-via spot within 5 mm; no path in 29x26 mm |
| 3 | `+3V3` | track F.Cu, (185.7, 145.4) | track B.Cu, (108.0, 162.5) | long haul (~77 mm): the brake-corner +3V3 users (R510/R533/R537) have no +3V3 plane under them (In2 there is +24V/+BATT); no path in a 114x89 mm window |
| 4 | `+3V3` | via F.Cu (75.3, 96.0) | R603.1 (72.6, 96.5) | no legal plane-via spot within 5 mm; no path in 34x20 mm |
| 5 | `+BATT` | track B.Cu, (103.7, 148.8) | via F.Cu (162.7, 138.3) | long haul (~59 mm): left logic branch (U1 buck input, TP_BATT1) to the +BATT plane at x 162; no path at 0.2-1.0 mm with Power_HV 0.25 clearance |
| 6 | `+BATT` | track F.Cu, (82.8, 117.8) | C3.1 (80.6, 113.1) | no legal plane-via spot within 5 mm; no path in 36x28 mm |
| 7 | `+BATT` | track F.Cu, (83.8, 117.8) | track F.Cu, (84.0, 121.5) | U1 input caps C4/R6 local: no path (U1 area full of autorouted tracks) |
| 8 | `/Brakes/BRK_OUT2` | U513.10 (201.0, 140.2) | J501.2 (209.0, 129.3) | no free start cell |
| 9 | `/Brakes/BRK_VREF` | R533.2 (187.0, 145.8) | track F.Cu, (199.5, 146.7) | 3 vias over budget |
| 10 | `/Brakes/VM_BRK` | U513.11 (200.3, 140.2) | C544.1 (200.9, 138.4) | no free end cell |
| 11 | `/Brakes/VM_BRK` | track B.Cu, (203.2, 132.8) | U513.11 (200.3, 140.2) | no free start cell |
| 12 | `/Bus_Breaker/BUS_SRC` | zone PWR_BRK_BUS_SRC F.Cu, | zone PWR_BRK_BUS_SRC F.Cu, | PWR_ pour split into islands (by autorouted tracks): needs copper, not a track |
| 13 | `/DRV_SCLK` | U302.28 (137.1, 87.8) | U701.78 (125.0, 114.7) | no path in 26x47 mm |
| 14 | `/DRV_SCLK` | U701.78 (125.0, 114.7) | U402.28 (142.9, 126.2) | no path in 26x21 mm |
| 15 | `/DRV_SDI` | U302.27 (137.1, 87.2) | U701.80 (126.0, 114.7) | no path in 20x36 mm |
| 16 | `/DRV_SDI` | U701.80 (126.0, 114.7) | U402.27 (142.9, 126.8) | no path in 25x21 mm |
| 17 | `/DRV_SDO` | R402.2 (148.0, 131.0) | U402.26 (142.9, 127.2) | no path in 24x22 mm |
| 18 | `/DRV_SDO` | U302.26 (137.1, 86.8) | R302.2 (132.0, 83.0) | no path in 24x22 mm |
| 19 | `/DRV_SDO` | U402.26 (142.9, 127.2) | U701.79 (125.5, 114.7) | no path in 26x22 mm |
| 20 | `/DRV_SDO` | U701.79 (125.5, 114.7) | U302.26 (137.1, 86.8) | no path in 20x37 mm |
| 21 | `/ESC_MCU/UART_RX` | track F.Cu, (139.8, 92.6) | U701.48 (125.0, 99.3) | no path in 43x20 mm |
| 22 | `/ESC_MCU/UART_TX` | U701.47 (125.5, 99.3) | J703.2 (158.5, 87.0) | no path in 42x22 mm |
| 23 | `/ESC_Motor_1/PH_A` | track B.Cu, (157.7, 75.0) | R316.1 (166.1, 84.4) | no path in 38x29 mm |
| 24 | `/ESC_Motor_1/PH_C` | R318.1 (162.6, 80.8) | track F.Cu, (139.2, 82.8) | no path in 47x21 mm |
| 25 | `/ESC_Motor_1/SPA` | zone PWR_M1_SPA F.Cu, | zone PWR_M1_SPA F.Cu, | PWR_ pour split into islands (by autorouted tracks): needs copper, not a track |
| 26 | `/ESC_Motor_1/SPB` | zone PWR_M1_SPB F.Cu, | zone PWR_M1_SPB F.Cu, | PWR_ pour split into islands (by autorouted tracks): needs copper, not a track |
| 27 | `/ESC_Motor_2/PH_B` | zone PWR_M2_PH_B_B B.Cu, | zone PWR_M2_PH_B_F F.Cu, | PWR_ pour split into islands (by autorouted tracks): needs copper, not a track |
| 28 | `/ESC_Motor_2/PH_B` | zone PWR_M2_PH_B_B B.Cu, | zone PWR_M2_PH_B_F F.Cu, | PWR_ pour split into islands (by autorouted tracks): needs copper, not a track |
| 29 | `/ESC_Motor_2/PH_C` | zone PWR_M2_PH_C_B B.Cu, | zone PWR_M2_PH_C_F F.Cu, | PWR_ pour split into islands (by autorouted tracks): needs copper, not a track |
| 30 | `/M1_ENABLE` | U702.4 (117.5, 96.0) | U302.30 (137.1, 88.8) | no path in 29x16 mm |
| 31 | `/M1_HALL2` | track F.Cu, (148.5, 80.4) | track F.Cu, (152.7, 85.7) | 4 vias over budget |
| 32 | `/M1_INLA` | U701.39 (129.5, 99.3) | U302.35 (139.8, 89.4) | no path in 19x19 mm |
| 33 | `/M1_INLB` | U701.41 (128.5, 99.3) | U302.37 (140.8, 89.4) | no path in 21x19 mm |
| 34 | `/M1_SENS_A` | C330.1 (142.1, 91.6) | U701.25 (137.7, 101.0) | no path in 32x31 mm |
| 35 | `/M1_SOA` | U701.36 (131.0, 99.3) | U302.23 (137.1, 85.2) | no path in 15x23 mm |
| 36 | `/M1_SOB` | U701.35 (131.5, 99.3) | U302.22 (137.1, 84.8) | no path in 14x24 mm |
| 37 | `/M1_TEMP_MOT` | track F.Cu, (141.0, 97.3) | C334.1 (135.3, 92.0) | no path in 29x29 mm |
| 38 | `/M1_nFAULT` | U701.2 (137.7, 112.5) | track F.Cu, (132.7, 91.4) | no path in 20x35 mm |
| 39 | `/M2_HALL3` | U701.93 (132.5, 114.7) | R431.2 (152.6, 128.3) | no path in 32x29 mm |
| 40 | `/M2_INLA` | U701.32 (133.0, 99.3) | U402.35 (140.2, 124.6) | no path in 16x34 mm |
| 41 | `/M2_INLB` | U701.53 (122.3, 102.0) | U402.37 (139.2, 124.6) | no path in 26x31 mm |
| 42 | `/M2_SOA` | U701.34 (132.0, 99.3) | U402.23 (142.9, 128.8) | no path in 19x38 mm |
| 43 | `/M2_SOB` | U701.31 (133.5, 99.3) | U402.22 (142.9, 129.2) | no path in 18x39 mm |
| 44 | `/M2_SOC` | U701.30 (134.0, 99.3) | U402.21 (142.9, 129.8) | no path in 17x39 mm |
| 45 | `/M2_TEMP_MOS` | track F.Cu, (129.4, 124.1) | U706.14 (141.6, 96.6) | no path in 22x37 mm |
| 46 | `/M2_nFAULT` | U402.25 (142.9, 127.8) | R401.2 (148.7, 128.7) | no path in 25x20 mm |
| 47 | `/M2_nFAULT` | U701.84 (128.0, 114.7) | U402.25 (142.9, 127.8) | no path in 23x22 mm |
| 48 | `/M2_nSCS` | U701.83 (127.5, 114.7) | track F.Cu, (143.0, 125.6) | no path in 30x21 mm; 4 vias over budget |
| 49 | `/Power_Supply/Q1_GATE` | R1.1 (165.5, 105.0) | D1.2 (90.6, 110.8) | no path in 95x23 mm |
| 50 | `BRK_FLT_N` | U513.4 (199.0, 145.8) | U601.16 (73.9, 92.8) | no path in 145x74 mm; 12 vias over budget |
| 51 | `DRV_EN_DLY` | JP501.3 (175.4, 145.8) | U703.2 (144.5, 116.6) | no path in 48x46 mm |
| 52 | `DRV_EN_DLY` | track B.Cu, (114.5, 99.2) | U703.2 (144.5, 116.6) | no path in 41x31 mm |
| 53 | `GND` | C334.2 (135.3, 90.4) | zone (GND pour) F.Cu, | no legal plane-via spot within 5 mm; no path in 31x33 mm |
| 54 | `GND` | C716.2 (133.5, 117.1) | U701.99 (135.5, 114.7) | no legal plane-via spot within 5 mm; no path in 30x31 mm |
| 55 | `GND` | U602.2 (89.9, 91.0) | zone (GND pour) F.Cu, | no legal plane-via spot within 5 mm; no path in 30x25 mm |
| 56 | `GND` | U701.99 (135.5, 114.7) | C706.2 (138.2, 116.9) | no legal plane-via spot within 5 mm; no path in 32x40 mm |
| 57 | `GND` | U706.5 (142.9, 102.4) | U706.2 (141.0, 102.4) | no legal plane-via spot within 5 mm; no path in 30x26 mm |
| 58 | `GND` | U706.5 (142.9, 102.4) | track F.Cu, (144.2, 102.4) | no legal plane-via spot within 5 mm; no path in 30x26 mm |
| 59 | `GND` | Y701.4 (140.2, 108.7) | U701.10 (137.7, 108.5) | no legal plane-via spot within 5 mm; no path in 30x29 mm |
| 60 | `GND` | zone (GND pour) F.Cu, | C440.2 (146.7, 126.7) | no legal plane-via spot within 5 mm; no path in 35x35 mm |
| 61 | `GND` | zone (GND pour) F.Cu, | C706.2 (138.2, 116.9) | no legal plane-via spot within 5 mm; no path in 32x40 mm |
| 62 | `GND` | zone (GND pour) F.Cu, | U2.2 (87.5, 114.9) | no legal plane-via spot within 5 mm; no path in 38x31 mm |
| 63 | `GND` | zone (GND pour) F.Cu, | U705.2 (119.2, 108.1) | no legal plane-via spot within 5 mm; no path in 29x35 mm |
| 64 | `GND` | zone (GND pour) F.Cu, | zone (GND pour) F.Cu, | F.Cu GND pour island with no legal stitch-via spot (via-ok cell inside the island) |
| 65 | `GND` | zone (GND pour) F.Cu, | zone (GND pour) In1.Cu, | F.Cu GND pour island with no legal stitch-via spot |
| 66 | `VBAT_IN` | U801.20 (193.3, 76.8) | via F.Cu (190.2, 77.8) | no legal plane-via spot within 5 mm; no free start cell; no path in 24x32 mm |

With `--rip-pour-crossers` the list is 79 rows. The table is in `/tmp/claude-1000/-home-mark-Documents-VE-V3/412ee8fb-27c0-4acd-98aa-e7fcd601bdf3/scratchpad/clean/varR/remaining.md`.

## Judgement calls
- **Rip versus widen:**
  - The 5 neck-downs that could not be widened were ripped. After that, M1_HALL2 (4 vias over budget) and M1_TEMP_MOT (no path) are unrouted where they used to be connected.
  - BRK_VREF (R533.2) was ripped for the U513 clearance and is now unrouted (3 vias over budget).
  - DRC errors were traded for listed hand routes.
- **High current:**
  - VM_BRK / BRK_OUT / +24V / +12V route at 1.5, then 1.0, then 0.6 mm. A 0.4 or 0.3 mm neck is allowed only on a pad-to-pad hop of 2 mm or less.
  - One VM_BRK route is 0.6 mm with 2 vias (3 A): widen it by hand.
  - BRK_OUT1 has a 0.6 mm piece.
  - U513 pins 10/11 (BRK_OUT2, VM_BRK) cannot be entered with 0.6 mm or more at 0.25 mm Power_HV clearance (0.65 mm pitch). They are listed.
- **Power-net tracks:**
  - +BATT routes at 1.0 mm (logic branch, below 1 A).
  - Phase / shunt sense taps (Power_HV / Power_Shunt class) route at 0.3, then 0.2 mm, because they carry signal current.
- **Via budget:** at most 2 + length/25 vias per route. BRK_FLT_N (176 mm) was found with 12 vias and rejected; it is better done by hand.
- **CAN_H:**
  - Rerouted alone: 4 vias, no longer coupled to CAN_L.
  - Fine at CAN speeds, but re-pair it by hand if the routes are redone.
- **Vias:**
  - +3V3 falls back to the Power_LV class via (0.6/0.3) where 0.8/0.4 does not fit.
  - No vias under other parts (courtyards) and none in pads. This is what leaves the 10 starved thermals and the 13 GND pads in dense spots without a plane via.
- **Added copper:**
  - It is unlocked and in the group `cleanup_routes`.
  - Freerouting's own tracks that were widened stay outside the group, and widening is a no-op on a re-run.
  - Pours, planes, critical_routes and PWR_VIAS are untouched.
