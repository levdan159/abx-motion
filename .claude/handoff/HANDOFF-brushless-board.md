# Handoff: abx-motion-brushless board (2026-10-23)

Repo `~/Documents/abx-motion`, branch `v1.0-bl-wip`, project `abx-motion-brushless` (KiCad 10.0.7 native).
**Nothing is committed.** Commit only if the owner asks. The owner reviews and commits.

## What the board is
Tracked high-payload rover controller. 10S Li-ion (36 V nominal, 42 V full), 2 brushless drive motors (6384 120KV, 30 A peak each).
- **ESP32-S3** (MCU.kicad_sch): app MCU, CAN to the ESC, RS-485, USB-C, OLED, buttons, odometry encoders J202/J203, I/O expander PCA9555 (Industrial_IO).
- **One STM32F405VGT6** (ESC_MCU.kicad_sch, refs 7xx). It runs VESC firmware in dual-motor mode (HW_HAS_DUAL_MOTORS) on the **Stormcore 60D pin map** (`hwconf/stormcore/60D`, base 60D: amp gain 10, shunt 1 mOhm).
  - Own hwconf needed: copy `hw_stormcore_60d_core.*`, then drop the smart switch (HW_EARLY_INIT/SWITCH_*), NRF, IMU and RGB LED.
  - Halls on both motors (stock VESC has ONE global encoder, so the encoders go to the ESP32).
  - Temps via 74HC4051 mux (U706). One CAN node. E-stop AND gates U702/U703.
- **2x power stage** (ESC_Channel.kicad_sch, instanced as ESC_Motor_1 refs 3xx / ESC_Motor_2 refs 4xx): DRV8323S (own RTA0040B footprint) + 6x CSD19532Q5B + 3x 1 mOhm shunts, J304/J404 hall + motor NTC.
- **Power.kicad_sch**: J1 battery solder pads (net **VBAT_IN**), F1 5 A + Q1 reverse P-FET -> +BATT -> 5 V buck U1 -> 3V3 LDO U2.
- **Bus_Breaker.kicad_sch (NEW, refs 8xx)**: TPS48111-Q1 (U801, own DGX0019A footprint).
  - Path: RSNS R801 0.5 mOhm -> back-to-back IPT015N10N5 TOLL Q801/Q802 -> **VBUS**.
  - Precharge: Q803 + R803/R804 (2x 10 R, 2512 anti-surge).
  - Trips: IOC 80 A / 5 ms, ISC 150 A, UVLO 28 V. IMON 30.6 mV/A.
  - Design notes and equations are on the sheet.
- **Brakes.kicad_sch**: LMR36520 24 V buck. Two TPS27S100A protected high-side drivers U504/U505 (ILIM 1.65k = 1.5 A), flyback D501/D502, J501/J502, fail-safe (coil on only while BRAKEn_EN AND +3V3_DRV_EN).
- **eFuses** MIC2009YM6 (abx symbol, replaced the PTC fuses): U205 +5V_ENC 0.5 A, U206 +3V3_EXT 0.25 A, U602 +5V_OUT 0.5 A.
- **Signal map**
  - ESP32: IO7 BUS_EN, IO2 PRECHG_EN, IO48 BUS_FLT_N, IO6 BUS_IMON (ADC), IO47 EFUSE_EN (100k pull-up), IO22 ESC_NRST, IO11/12 BRAKE1/2_EN, IO13 ESTOP_SENSE.
  - PCA9555: IO1_2 EFUSE_FLT_N, IO1_3 BRK_FLT_N.
  - IO45/IO46 (strapping) are free.

## Current state
- Schematic: **ERC 0 errors**. Warnings: 14 lib_symbol_mismatch, 1 VBAT_IN/V_RAW_IN multiple names (old). 385 parts, netlist verified net by net.
- **PCB is BEHIND the schematic**: the owner must press **F8 (Update PCB from Schematic)** in the PCB editor opened from the project window (standalone eeschema cannot F8).
  - F8 adds the breaker, brake-driver and eFuse parts unplaced.
  - Stale footprints (old Q501/Q502, R504/R506, F3/F4/F5) must then be removed.
- PCB layout so far: 4 layers (2 oz outer, ENIG), 157 x 118 mm (x45-202, y48-166). Floorplan:
  - Left column: ESP32/IO.
  - Strip x96-114: logic power supply.
  - ESC1 power stage: x115-177, y48-94 (DRV at bottom).
  - Shared STM32 strip: y94-118.
  - ESC2: y118-164, mirrored (DRV at top).
  - Right strip: J1 battery pads (191,104), J102 E-stop terminal, test points, brakes block (y118-158, J501/J502 on right edge).
- GND pours on F.Cu, In1 and B.Cu. **In2 empty** (planned power planes). **Nothing routed.** DRC: only 16 starved_thermal (FET pads; fix with power pours).

## Done 2026-10-23 (session 2)
- F8 done; stale Q501/Q502/R504/R506/F3/F4/F5 removed via API. Parity DRC 0, 385 footprints.
- Placed by `bl/place7.py` (backup before it: `bak/pcb.pre_place7.kicad_pcb`):
  - Breaker power column x178-189: J1 rot 270 (BAT+ on top) -> R801 (horizontal, y89) -> Q801 (rot 270, y79.6) -> Q802 (rot 90, y65.3, VBUS drain up toward ESC1 bus caps).
  - U801 rot 180 at (195.5,66) + 20 passives in x190-201; precharge R803/R804/Q803 left of the column (x168-177, y76-91).
  - U504/U505 rot 180 at the old Q501/Q502 spots (OUT faces J501/J502); U502/U503, R503/R505, R508/R509, C510/C511, R510 re-placed round them.
  - eFuses: U205 group (58,122), U206 group (63,112), U602 group (91,115).
  - TPs row y122.5 x97-113; J102 bottom edge (58,160, rot 0, wire entry down); LOGO1 to (76,90).
- Zones refilled. DRC: 0 clearance/courtyard/short; left: 18 starved_thermal (FET pads), silk noise, 126 lib_footprint_mismatch.
- Backups of the old session's /tmp copied to `.claude/handoff/bak/`.

## Next steps
1. Owner eyeballs the placement (render: `kicad-cli pcb render --side top`).
2. ~~F8, stale removal, placement~~ done.
3. In2 power planes (VBUS, +BATT, +5V, +3V3, +24V), high-current pours for phases/VBUS, then routing. Silk ref cleanup after routing.
4. Before fab:
   - verify the MIC2009 EN polarity (ordering suffix), IPT015N10N5 Qg (169 nC assumed), and the TPS27S100 PWP thermal pad vs TI's PWP0014 drawing;
   - confirm the stackup with the fab;
   - write the VESC hwconf: **max input voltage 46-48 V** (stops regen before VBUS can climb; the breaker's back-to-back FETs block regen into the pack when open, D301/D401 SMCJ43A only trim spikes);
   - **F1: fit a 58 V-rated ATO blade fuse** (standard blades are 32 VDC; pack is 42 V full); confirm the part number and the Keystone 3557-2 holder voltage rating;
   - confirm Q1 SQJ459EP V_DS rating (assumed 60 V);
   - Degson DG135T: confirm the row spacing (drawing 10.16, STEP model 9.66) on a physical sample before ordering boards; no 3D models on the terminal footprints yet;
   - (obsolete: REDCUBE J1) J1 footprint: shrink the 4 side pads (at 4.43 mm from each M5 hole) 3.2 -> 3.0 mm to clear the 0.25 mm hole rule, then update the footprint on the board.
- VBUS TVS added (`bl/tvs.py`, sheet backup `bak/sch_pre_tvs/`): D301 at the breaker output above Q802 (182.8,52.2), D401 at (165,132.5). No room at the stage caps; fine for slow regen pump-up via the VBUS plane. DRC clean (copper), parity 0, 387 parts.
- Whole-board placement pass (`bl/place8.py`, backup `bak/pcb.pre_place8.kicad_pcb`), owner's left side kept:
  - ESC1 top / ESC2 bottom = 180 deg copy about (140,107). Phase lugs J301-303 / J401-403 (REDCUBE M4 74650074, 50 A) on the edge at y55.2 / 158.8, x 123/141/159.
  - Each phase: high|low FET side by side (rot 180: drain left, PH node between, source right), shunt under the low FET, 1210 caps under the high drain, DRV rot 180 (gates up).
  - STM32 U701 (140,107) rot 180 (shortest ratsnest), bulk caps C328/C329/C428/C429 in the x96-112 column, D401 (104.5,147.5).
  - J1 = 2x REDCUBE M5 (`abx-footprints:ABX_REDCUBE_M5_x2_P18mm`, origin = pad 1 BAT+) at (194.5,94) rot 270, input protection F1/Q1/D2/R1 beside it.
  - DRC after F8 + refill: 0 clearance/overlap/short, parity 0; 32 hole_clearance inside J1 = Wurth M5 land pattern (side pads 0.18 mm from the thread hole; rule 0.25).
- Terminals changed to screw clamps (owner, after the 3D view): Degson DG135T-10.16 (57 A IEC / 52 A UL, 10 mm2), footprints `abx-footprints:ABX_Degson_DG135T-10.16-03P` / `-02P` (drawn from Degson's PCB layout: 2 holes per pole, 10.16 grid, 2.4 drill; 02P pads numbered from the far end so BAT+ is on top). LCSC C528720 = 03P.
  - Schematic: J301 = one 3-pole Screw_Terminal_01x03 (PH_A/B/C) per stage (J302/J303/J402/J403 removed; `bl/terminals2.py`, `bl/regen_esc_channel.py`); J1 footprint -> 02P.
  - Placement v2 `bl/place9.py` (+ `bl/rotopt.py` rotation pass, `bl/fill.py` zone refill): J301 (150.16,50.93) rot 180 / J401 (129.84,163.07) rot 0, J1 (199.07,107.2) rot 90; FET row y66.9, shunts horizontal y72.1; U701 (130,107). DRC: 0 copper/courtyard/hole errors, parity 0. Backup `bak/pcb.pre_place9.kicad_pcb`.
- 117 hidden ref fields were unhidden on silk (2026-10-23; LOGO1/LOGO2 stay hidden): silk cleanup after routing.
- Position snapshot/diff of the live board: `bl/posdiff.py snap|diff` (snapshot in `bak/pos_snapshot.json`).

## How to work (important)
- **Live editor: use the KiCad IPC API (kipy), never desktop screenshots.**
  - `~/.cache/mark-mods/kicad-mcp-big-venv/bin/python`, `from kipy import KiCad; b = KiCad(timeout_ms=120000).get_board()`.
  - Methods: `get_footprints()`, `update_items`, `remove_items`, `save()`, `revert()`, `refill_zones()`.
  - No `begin_commit` while the schematic editor is open (it errors).
- Bulk edits: pcbnew python on the saved file (same venv; system python3 has no pcbnew), then `b.revert()` in the live editor. Never let a stale editor save over file edits.
- pcbnew quirks: `b.Remove(footprint)` fails (use the API or text removal); create zones in a separate process (`bl/zones.py`); `LoadBoard` needs the `.kicad_pcb` extension.
- `kicad-cli sch erc` / `pcb drc --schematic-parity` / `pcb render` for checks. Always write DRC JSON to a **fresh** path (a stale report fooled me once).
- Schematics are generated: `bl/schgen.py` (Sheet: deterministic uid('sym', ref) symbol UUIDs, `uuids` override, `existing_uuids()`, `inject()` into hand-drawn sheets).
  - Generators: `bl/esc2.py` (power stage + ESC_MCU + root), `bl/fuses.py` (breaker, brakes, eFuses; **not idempotent**: restore from backup before re-running), `bl/symgen.py` (abx symbols + DGX footprint).
  - Placement: `bl/place5.py` / `bl/place6.py` (ESC area: block() spiral placer with anchors), `bl/zones.py`.
  - Helpers: `bl/netparse.py` (netlist), `bl/schq.py` (pin positions).
- Datasheet text extracts: `ds/` here (tps4811, tps27s100, mic20xx, drv8323). VESC firmware source was in the old session scratchpad (`vesc-src/`); re-clone `github.com/vedderb/bldc` if needed.
- Copies of the scripts are in `.claude/handoff/bl/`. They have hard-coded scratchpad paths in places: fix the paths when reusing.
- Backups from the old session (may vanish with /tmp): `/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/` (bak_dual/, bak_efuse/, pcb.pre_*).
- Owner preferences: terse replies; no commits; confirm before big redesigns; prefers recommended option with reasoning.

## Done 2026-10-23 (session 3): aux power + one brake output + category-1 E-stop
- Decision (owner): MVP brakes are firmware (regen / phase short); hardware supports either spring-applied coil brakes (motor with built-in brake, e.g. ZLTECH ZLLG80 8" hub ~$110 — confirm halls, coil V/I, 42 V OK) or e-scooter disc calipers + actuators. One brake output, both brakes in parallel (symmetric). Motors MUST have halls (VESC encoder commutation only on motor 1); odometry encoders already go to the ESP32 (J202/J203).
- `bl/aux.py` regenerates **Brakes.kicad_sch** (sheet name kept; hier pins unchanged): U511 TPS54560B +24V (4 A cont / 5 A peak, 400 kHz) -> J510 XT60PW-F (powers the v1.1 board: v1.1-final takes 12-30 V on +BATT; limit = D2 SMCJ30A TVS, 30 V standoff ~33 V breakdown; then DRV8701 + DRV8825 45 V; LMR36520 65 V, CSD18540 60 V, bulk caps 50 V — checked 2026-10-24 from the v1.1-final PCB); U512 TPS54360B +12V 3 A -> J511; U513 DRV8874 PWM mode (IN1/IN2 = BRAKE1_EN/BRAKE2_EN, ITRIP 3 A, fixed off-time), J501 4-pole (1-2 brake A, 3-4 brake B), supply jumper J512 (24/12 V) via blocking D523 SS54, D522 SMBJ28A + C546 100 uF absorb coil energy; JP501 nSLEEP = E-stop immediate (default) or DRV_EN_DLY. Values + calcs: `.claude/handoff/aux_design.md`. Removed: LMR36520 brake buck, U502-U505, D501/D502, J502, R501-R509 (except R507), C501-C511.
- **Category-1 E-stop** (`bl/esc2.py` + `bl/regen_esc_mcu.py` regenerates only ESC_MCU): DRV_EN_DLY = 74LVC1G17 (U707) after R709 150k / C724 10 uF on +3V3_DRV_EN (~1.7 s off delay, ~1 s on) gates both DRV ENABLEs; STM32 PE15 = ESTOP_OK (immediate, via R710 1k) so firmware brakes first.
- Power: F1 now 10 A 58 V ATO (Q1 SQJ459EP ~1.1 W at 7 A: give it copper). Net classes: +24V, +12V, /Brakes/SW_*, VM_BRK, BRK_VSEL, BRK_OUT* -> Power_HV.
- Backups: `bak/sch_pre_aux/`. ERC: only the old lib_symbol_mismatch + VBAT_IN/V_RAW_IN warnings.
- Next: owner F8 (Replace footprints + Delete footprints with no symbols), then place the new block (right strip, old brakes area y118-158) and re-run DRC. Firmware owed: ESTOP_OK -> brake within ~1.5 s; brake driver IN1/IN2 logic; actuator stall cut-off (time / limit switches on the I/O inputs).
- Before fab add: check PDS5100H / MWSA1265S / MWSA1005S specs + LCSC stock; XT60PW-F pad 1 polarity vs v1.1 input; U511 thermal (pour + vias).
- **2026-10-24 PCB:** scripted F8 `bl/f8.py` (adds/replaces/removes footprints + all pad nets from a kicadxml netlist; sets FPID nickname, sheetname/file; parity 0 = same as GUI F8). TP_GND2 was missing from the saved board: re-added at (109.7,158.3). **Board widened 12 mm right (owner): outline x45-214** (`bl/widen.py`: Edge.Cuts, GND zone outlines, J1/H2/H4 +12 mm). `bl/place10.py` placed the aux block: J501 brakes + J511 12 V on the right edge under J1 (x 209), J510 XT60 on the bottom edge (x 185-202), C525 in J1's old slot by F1/Q1, 24 V buck row y~115-128, 12 V row y~129-142, DRV8874 by J511; E-stop delay parts by U702/U701. U511 footprint -> TI_SO-PowerPAD-8_ThermalVias (same DDA0008B as U512; the R-PDSO-G8 one violated 0.25 mm Power_HV clearance EP-to-pin). DRC after fill: no clearance/courtyard/hole errors, parity 0. Snapshot refreshed. Tweak candidates: VM_BRK parts (D523, C546, D522, C545, R534/R536) ended up spread out — pull toward U513 when routing.
- **3D models (2026-10-24):** `bl/models3d.py` (needs an OCP venv: `uv venv cadenv --python 3.11 && uv pip install cadquery-ocp`) builds `3dmodels/Degson_DG135T-10.16-02P.step` (Degson STEP id 2151301 is the 2-pole despite its 03P header; re-oriented to the footprint frame), `-03P.step` (two 2P fused one pitch apart) and `AMASS_XT60PW-F_simple.step`. `bl/attach3d.py` sets them on the abx Degson library footprints + J1/J301/J401/J510 and restores missing std-lib models (C340-342, C440-442, D301, D401). Model colours are lost (grey). The STEP's row spacing is 9.8 mm vs 10.16 in the drawing: still measure a sample.
- **J510 -> green Phoenix MKDS-1,5-2-5.08 screw terminal** (owner, 2026-10-24) at (190, 160.96) rot 0, wire entry on the bottom edge (XT60 model file kept but unused). File-editing scripts now refuse to run while `kicad` is running (pgrep guard).
- 3D gaps closed (2026-10-24): U511/U512 -> KiCad TI_SO-PowerPAD-8.step, U513 -> HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm.step (the library footprints point at retired .wrl names); `bl/models3d_ic.py` builds simple bodies `3dmodels/D_PowerDI-5_simple.step` (D520/D521) and `TI_DGX0019A_VSSOP-19_simple.step` (U801, also set in the abx library footprint). Only holes, TPs, JP501 and logos have no model (by design).
- **In2 planes (2026-10-24, `bl/planes.py`, re-runnable):** +3V3 left logic column x45.5-100; VBUS x100-178 (to 189 at Q802/D301 for y<75) incl. under the STM32 strip; VBAT_IN breaker + J1 BAT+ (top right); +BATT x162-198 y91-150 (Q1, D2, C525, buck inputs); +24V x162-203 y105.5-165.5 (L520 out caps -> J510, brake corner). +12V, VM_BRK, +5V, +3V3_ESC = traces. Planes are islands until routing adds vias (isolated_copper warnings).
- **Routing, stage 1+2 (2026-10-24, on the real board; backup `bak/pcb.pre_crit_pours`).** Order is fixed: `planes.py` (deletes every In2 zone) -> `buckplace.py` (pending) -> `critical.py <board>` -> `pours.py <board>`; each re-run rebuilds its own items (group `critical_routes`; zones `PWR_*` + group `PWR_VIAS`). critical: gate drive / SH Kelvin / SP-SN / DRV local caps / VCP / VM, STM32 crystal / VCAP / NRST, part of the buck nets (the agent moved gate resistors, DRV caps, sense passives, crystal caps: `critical_report.md`). pours: 61 locked zones + 549 vias (phases F+B, VBUS, shunt/GND, breaker on B.Cu+In2, buck SW nodes, +BATT/+24V/+12V; small In2 VBUS strip under Q405): `pours_report.md`. DRC: no copper errors, parity 0, starved_thermal 8.
- Open from these: buck FB/COMP/CZ/BOOT_12/RT_12/EN_24 unrouted (placement: agent on `buckplace.py`); SNx = GND in the schematic, so no true Kelvin return (needs a net-tie per shunt: owner); high-side gate vias under J301/J401 bodies (tented); VBAT_IN, BUS_SRC, BUS_SNS not in Power_HV; In2 planes use thermal spokes on THT pads (J1 BAT+: consider solid).
- Freerouting (stage 3): first trial on the unrouted board timed out (pass 1 = 1120 s, 281/748 left; it tried 2 mm Power_HV traces). Pre-routes export as `(type fix)` once locked; pours export as planes, In1/In2 set to LT_POWER on the export copy only.
- **buckplace (2026-10-24, applied; backup `bak/pcb.pre_buckplace`):** `bl/buckplace.py` moves 31 buck parts to the TI layout (diode above IC, BOOT cap between pin 8 and L, VIN caps at pin 2, EN pin 3, RT pin 4, FB/COMP/CZ row under pins 4-6); U511/U512 moved 2 mm down. critical.py now routes 64/64; pours.py buck section rewritten for it. Report: `buckplace_report.md`. Still open: +24V/+12V Vout sense to R523/R529 (Freerouting / by hand). Real-board DRC: no copper errors, parity 0, starved_thermal 7.
- **Freerouting imported (2026-10-24; backup `bak/pcb.pre_autoroute`, session `bak/autoroute_2026-10-24.ses`):** `bl/autoroute.py export|import` (locks all pre-routes first: KiCad then keeps them and adds only new wiring; groups survive). 20 passes / 2.2 h: 4196 items (491 vias), unrouted 511 -> 195 (GND 84, +3V3 40, +BATT 10, VM_BRK 6, VBAT_IN 5, ~50 signals). Its 143 "pre-existing violations" are Freerouting's view of the locked pre-routes (KiCad DRC: none). After import DRC: 18 track_width neck-downs, 6 clearance at U513, CAN_H over LOGO1 copper (short), starved_thermal 60. All tracks are now locked except Freerouting's. Next: `bl/cleanup.py` (agent, report `cleanup_report.md`).
- **Cleanup applied (2026-10-24; backup `bak/pcb.pre_cleanup`):** `bl/cleanup.py <board> --rip-pour-crossers` (~20 min; group `cleanup_routes`, unlocked). It removes the DRC violators, fixes neck-downs, adds 112 plane fanouts + starved-pad stubs + stitch vias + 35 routes, and with the flag rips Freerouting tracks that split other nets' pours (halls/enables through the phase pours, BUS_SRC between Q801/Q802 and the shunts) and routes them outside (chosen over the default: whole pours > 13 fewer airwires). **Real board now: 0 copper DRC errors, parity 0, starved_thermal 10, 79 unrouted** (list + reasons: `cleanup_report.md`; mostly ~35 signals in the U701/U302/U402 block with no free channel, 13 GND pads with no via spot, split power pours, long BRK_FLT_N / Q1_GATE / DRV_EN_DLY, U513 pins 10/11 VM_BRK entry; one VM_BRK route is 0.6 mm: widen by hand).
- Full script pipeline from a placed board: planes -> buckplace -> critical -> pours -> autoroute export / Freerouting / autoroute import -> cleanup --rip-pour-crossers. `bak/pos_snapshot.json` is stale (buckplace + critical moved parts): refresh with `bl/posdiff.py snap` once the board is open.
- Next: hand-route the 79 (or loosen the U701 block placement first), owner decisions below, then silk / reference cleanup and a fab-rule DRC.
- Owner decisions open: SNx Kelvin net-ties (SNx = GND now); VBAT_IN / BUS_SRC / BUS_SNS into Power_HV; solid (not spoke) In2 connection on J1 BAT+; high-side gate vias under J301/J401 bodies (tented).
- **Tooling direction (owner, 2026-10-24):** KiCadRoutingTools for routing (from-scratch test + compare in `~/Documents/abx-motion-routetest/REPORT.md`; hybrid run = our rules/pre-routes + KRT with temporary keepouts over PWR_* pours, F/B only — on hold until the owner reviews the comparison), Konnect for Claude's KiCad edits (trial pending), OrthoRoute no. Long-term: scripts become rules + verification; placer/router do the geometry.
- **KiCadRoutingTools test done (2026-10-24, `~/Documents/abx-motion-routetest/REPORT.md`, table `runs/cmp_all.txt`):** from scratch F/B-only (r5) = 39 unrouted, 0 copper DRC errors, but no power pours (phases/VBUS/+BATT on 0.2 mm necks), gate loops up to 145 mm² vs ours 26-64, GND outer pours in 75/76 pieces; free-layer run (r4) = 12 unrouted but 279 clearance errors + 4 m of signal on In1/In2. Verdict: KRT for leftover signal nets + its QFP fanout (main-pass fails 72 -> 1), not full routing. TRAP: every KRT step rewrites the .kicad_pro rules (clearance 0.15, hole clearance 0.25->0.15) unless `--no-fix-drc-settings`. Ours: 39 segments / 15 nets cross other nets' non-GND pours (91 mm, likely locked critical routes) — review. Hybrid (`routetest/scripts/krt_route.py`, dry-run only) on hold for the owner.
- **Placer + hybrid test stopped by the owner (2026-10-24 20:2x)** in `~/Documents/abx-motion-routetest/runs/p1-p3` (scripts `routetest/scripts/placed_hybrid_*.py`, `run_placed_hybrid.sh`). Placer: 7 seeds (scattered ~8 min, clustered 22 min each), judge picked s0; logic moved, locked power side untouched. Hybrid routing with rules (locked copper, pour guard, keep-away 1 mm, sense groups, --no-fix-drc-settings): main pass 87 min / 6.4 GB peak, 46 nets still failing — ~36 of them STM32 <-> both DRVs (gate commands, SO/SENS ADC, halls, SPI, faults) + breaker logic. No REPORT_placed_hybrid.md. Diagnosis: 2 signal layers + STM32 pin assignment ignores driver sides + In2 under the STM32 block is VBUS so +3V3_ESC runs as tracks. Levers: STM32 pin swap (owner: schematic + firmware), In2 +3V3_ESC island under the STM32, keep-away 0.5 mm there, or 6 layers. Real board untouched.
- **ESP32 / Industrial_IO / Sensors + 12 V buck removed (2026-10-24 late, report `esp_removal_report.md`, backup `bak/pre_esp_removal/`).** 135 parts gone (U3, U601, U512 block, J511, J512...); CAN J205/J204/R219 and USB-C J201/U201/R201/R202/F2/D202 moved to ESC_MCU (same refs, PCB positions kept) + R711/R712 PA9 VBUS divider (staged x225). STM32: PE5/PE6 BRAKE1/2_EN (TIM9), PD10 ESTOP_SENSE, PD8 BUS_FLT_N, PA11/12 USB, U706 A4 VBAT_SENSE / A5 BUS_IMON. CAN_H/CAN_L/NRST are now `/ESC_MCU/*` nets. D523 from +24V. BUS_EN/PRECHG_EN undriven (TODO note on Bus_Breaker), BRK_FLT_N pull-up only (propose PD9). PCB: `bl/f8.py` (now re-paths moved symbols, re-nets copper) + new `bl/espclean.py` (dead-net / U512-pour / dangling copper); ERC 0 errors, DRC parity 0, no copper errors, 82 unrouted, starved_thermal 9. buckplace/critical/pours de-12V'd and verified on a copy (not re-run on the real board).

## 2026-10-24 (late): owner-approved additions (report: `additions_report.md`; backup `bak/pre_additions/`)
- **BRK_FLT_N -> PD9** (R510 pull-up kept).
- **Autonomous bus breaker.** The TPS48111 has no built-in precharge->main sequencing (INP/INP_G are independent; TMR = OC timer only). New `bl/breaker.py` regenerates Bus_Breaker (fuses.py's breaker section is now stale).
  - UVLO R806 300k / R807 12k: 30.7 V on / 28.9 V off.
  - U802 LM339 sequencer: precharge until VBUS = 92 % VBAT, then INP on (sticky to ~45 %); 0.18 s precharge timeout latches off into a short; UV gate at 26.8 V.
  - Check the R803/R804 pulse rating (88 W, 0.18 s).
- **ESC_MCU** (`bl/esc2.py` + regen_esc_mcu.py):
  - IMU U711 LSM6DS3TR-C on I2C1 PB8/PB9, INT1 PE4, 0x6A;
  - I/O header J704 JST PH 8P (PE0 PE1 PE2 PD15 PA15 PB13, 100 R + 3x USBLC6-2SC6, +3V3 via F701 200 mA PTC).
- **+5V_AUX** (new `bl/aux5v.py`, injected into Power, paper A2): U901 = copy of U1 LMR36520 from +BATT -> U902 MIC2009 eFuse (2.0 A typ, FAULT -> PD11) -> D901 SMAJ5.0A -> J511 "5V_AUX".
  - No current margin (LMR36520 = 2 A rated; no 65 V pin-compatible sibling: proposal TPS54360B).
  - LMR36520 / SRP7028A-150M are not in the JLC DB.
- **PCB:** f8.py (stages right of existing off-board parts), 55 parts staged at x 240-340, not placed. Parity 0, no copper errors, unconnected 82 -> 224 (all new parts). Locked groups unchanged.
- ERC 0 errors (new warnings: 4 lib_symbol_mismatch of the U201/Q8xx kind, 2 pin_to_pin on U711 SA0/SDX = GND).
- Pins still free: PA10, PB2, PB5, PC14, PC15, PD5, PD6, mux A6.

## 2026-10-24 (late): TPS54360B 5 V bucks, TPS25200 eFuse, pulse-rated precharge (report: `tps54360_report.md`; backup `bak/pre_tps54360/`)
- **U1 (board +5V) and U901 (+5V_AUX) = TPS54360BDDAR (C524806), one BOM** (LMR36520 / SRP7028A were not at JLC).
  - 494 kHz (RT 196k), 5.00 V (53.6k / 10.2k).
  - L 10 uH MWSA0603S-100MT; D PDS5100-13 (100 V 5 A).
  - Cout 2x 47 uF/10 V; Cin 2x 4.7 uF/100 V + 100 nF.
  - Comp 9.1k + 10 nF // 68 pF.
  - UVLO 560k / 33k: 20.9 V on / 19.0 V off.
  - The hand-drawn LMR U1, C5 and L1 are gone. New parts: U1, L1, D3, R10-R13, C11, C12 (Power sheet, x 375-510). R4/R5/C2-C4/C6-C8 re-valued.
- **U902 MIC2009 -> TPS25200DRVR (C128401).** RILIM 39k: 2.33 / 2.49 / 2.65 A. The MIC2009 tops out at 2.0 A.
- **Precharge:** R803/R804 (2x 10 R 2512: 44 W each into a short, about 30 W allowed at 0.2 s) -> 4x Yageo SR2512JK-077R5L 7.5 R (R803, R830, R831, R804 = 30 R).
  - 14.7 W / 2.6 J each into a shorted bus: 2x margin.
  - Precharge to 92 % takes about 120 ms incl. BST, inside the 0.16-0.20 s timer.
- **Scripts:** `bl/aux5v.py` rewritten (idempotent; one-time migration of the old injection); `bl/breaker.py`; `bl/pours.py` skips the U1 EP zones while U1 is off-board (tested on a copy); new `bl/tpsclean.py` (old U1 loop copper, PRE_M copper, dead +BATT stub, U1 EP zones).
- **PCB (f8 + tpsclean):** 17 new footprints staged at x 355-380 (U901/L901/U902 replaced in place off-board).
  - Parity 0, no clearance/short, starved_thermal 9 (same pads), unconnected 224 -> 262.
  - critical_routes / PWR_VIAS unchanged.
- **ERC:** 0 errors, warnings unchanged (14 / 2 / 1).
- **Open:**
  - Place and route the new U1 loop.
  - SR2512 7.5 R stock is only 863 (fallback 3x 10 R SR2512).
  - D2 SMCJ43A clamps above the TPS 65 V abs max at full Ipp.

## 2026-10-25: +24V buck U511 -> TI LM70880RRXR, 6 A continuous / 8 A short-term (report: `lm70880_report.md`; backup `bak/pre_lm70880/`)
- **Schematic** (`bl/aux.py`, Brakes sheet): LM70880 500 kHz, 10 uH TMPC1265HP-100MG-D, 5 mOhm 1206 shunt R538 (L520 -> ISNS_24 -> R538 -> +24V), FB 348k/12k, comp 4.42k/15nF/100pF, UVLO 267k/10k (27.7/24.9 V), RT 43.2k, CONFIG 41.2k (spread spectrum), CBOOT 47nF + R539 1R, C550 VCC 4.7uF, C551 VDDA 100nF, BIAS/PFM = GND, PG open. 4x 4.7uF/100V in, 5x 10uF out. **D520 removed.** Every block part has a hidden LCSC field (all in stock; J510 only 197). New symbol `abx:LM70880RRXR`, footprint `abx-footprints:TI_RRX0029B_VQFN-29_6x6mm_P0.5mm_ThermalVias` (`bl/lm70880fp.py`). `/Brakes/ISNS_*` -> Power_HV.
- Datasheet re-check fixed: die-pad map, pad 12/13 0.213 mm (0.2 local clearance), dropout 25.1 V typ, PG pull-up dropped, R538 location.
- **PCB (real board):** f8 (now copies symbol fields; parity 0) + new `bl/lm70880clean.py` (old block routes, pours and pour vias, L520-pad-2 +24V vias, old R523 sense line; U511 staged at (395,122)). DRC: parity 0, no copper errors, starved 9, unconnected 262 -> 301.
- **buckplace / critical bucks() / pours section 5 rewritten for the LM70880, tested on a copy only** (67/67 routed incl. the ISNS/VOUT Kelvin pair on B.Cu; 57 zones / 538 vias; DRC 0 copper errors, parity 0, unconnected 265, starved 12). Not run on the real board.
- Open: F1 stays 10 A (15 A only for 8 A continuous); J510 pin 1 hangs on 0.4 mm In2 spokes (make it solid / add an outer pour); optional PG -> STM32. v1.2 power interface spec: `v12_power_interface.md`.

## 2026-10-25: staged parts placed (report: `placement_report.md`; backup `bak/pre_placement/`)
- **All 80 off-board parts are on the board** (real board = the tested copy; KiCad closed). The pipeline is now
  `bl/newplace.py` (new) -> `buckplace.py` -> `critical.py` -> `pours.py` -> `fill.py`. It is idempotent: a second pass
  gives identical copper.
- **U1 / U901 TPS54360B** in the left logic column (U1 above the U2/LED cluster, U901 below it, turned 180 deg).
  - Layout: TI SNVSB93 fig. 52, with the old U512 offsets kept, so its pours and routes can be ported as a translation.
  - The +5V_AUX chain U902 / D901 runs to **J511 on the left edge**.
- **U802 sequencer** sits right of U801 (x 202-213). **R830/R831** sit below R803. **IMU U711** is right of U701.
  **R711/R712** are by LOGO1 (13.6 mm from PA9). **J704** is on the top edge with its ESD and series resistors.
- **U511 LM70880 block placed** (`buckplace.py`); critical.py routes 67/67.
- `pours.py`: U901 EP zones, and an EP-to-pin-7 strip for both TPS54360B. No other new copper.
- DRC:
  - parity 0; no clearance, short, courtyard or hole errors;
  - unconnected 301 -> 219;
  - starved_thermal 9 -> 15: the LM70880 C521/C550/C551, C909, and U1/U901 pin 7 (pour spoke count only).
- KRT `check_floorplan --intent` (hand intent `placement_intent.json`): 0 errors. `check_assembly`: buildable.
- **Owner decision:** USB-C J201 to the top edge.
  - Placed on a copy only: `newplace.py --usb-top`, render `png_placement/placement_top_usbtop.png`.
  - CAN stays where it is (gain <= 12 mm).
- Next steps:
  1. Port the U512 hot-loop pours and routes to U1/U901 (D902/D3 need their SW/GND copper, ~1.3 W).
  2. In2 re-plan (left column +3V3 -> +BATT island; optional +3V3_ESC island under U701, VBUS cross-section caveat).
  3. Route the 219.
- Renders: `png_placement/`.

## 2026-10-25: USB-C to the top edge (owner approved)
- `newplace.py` now always applies USB_TOP (flag removed); pipeline re-run on the real board (backup `bak/pre_usbtop/`). DRC: parity 0, no copper errors, unconnected 230, starved_thermal 19 (+4 = J201 GND pads A1/A12/B1/B12, fix with GND vias when routing).

## 2026-10-25: whole-board KRT placement trial: no-go (stopped by owner)
- Sandbox: scratchpad fullplace/. Same quick-route judge on all: KRT whole-board seeds failed 82 (s3) / 91 / 95 / 97 nets, each with 2-4 floorplan errors; our current placement (copper stripped) 87 with 0 floorplan errors. Recurring failures on every seed: IMU_INT1, VCAP2, DRV DVDD = STM32/DRV congestion, not a seed problem.
- Next experiment (running): power-right / logic-left split with our blocks as rigid templates, scratchpad split/ (REPORT.md, floorplan_rules.md).
