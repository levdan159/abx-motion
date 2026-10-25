# START HERE: abx-motion-brushless (handover 2026-10-25)

New session: start Claude Code in `~/Documents/abx-motion` (the routing skills in `.claude/skills/` load there).
Read this file, then the tail of `HANDOFF-brushless-board.md` (full history) only when you need detail.

## What the board is
- 36 V 10S, 4 layers (F.Cu / In1 solid GND / In2 power / B.Cu), branch `v1.0-bl-wip`, project `abx-motion-brushless`.
- Role: dual VESC (one STM32F405, 2x DRV8323S, 6 FETs + 3 shunts per motor) + power for the v1.2 board.
- v1.2 (actuators/steppers) belongs to someone else: never edit it. Its ESP32 commands this board over CAN (VESC protocol).

## Decisions made (owner)
- Removed: ESP32 sheet, Industrial_IO, Sensors, 12 V output.
- STM32 takes over:
  - brakes: PE5/PE6;
  - E-stop sense: PD10;
  - bus fault: PD8;
  - brake fault: PD9;
  - VBAT and bus current: mux A4/A5;
  - USB: PA11/PA12, with VBUS detect on PA9;
  - aux eFuse fault: PD11.
- Added:
  - hardware-autonomous bus breaker: TPS48111 + LM339 sequencer, UVLO 30.7/28.9 V, precharge 4x 7.5 R SR2512;
  - I/O header J704: PE0-2, PD15, PA15, PB13;
  - IMU LSM6DS3TR-C on I2C1 PB8/PB9, INT1 on PE4. Not 9-DOF: a magnetometer is useless near the motor currents.
- Bucks:
  - U1 (+5V board) and U901 (+5V_AUX 2 A, eFuse TPS25200 at 2.33 A min) are both TPS54360B;
  - U511 (+24V out to v1.2) is LM70880.
  - 24 V rating: 6 A continuous / 8 A short-term. 7.5 A was checked and rejected (Tj 128-134 C).
  - The rating covers the whole rail, brakes included.
  - v1.2 must keep its DC-motor start current within that (spec: `v12_power_interface.md`).
  - F1 stays 10 A.
- USB-C moved to the top edge.
- Firmware owed (VESC hwconf + Lisp):
  - brake PWM hold (~150 ms full, then ~50 %);
  - ESTOP_OK -> brake;
  - CAN timeout 200-300 ms with brake current;
  - breaker monitoring.

## Board state (real board)
- Checks: ERC 0 errors. DRC: schematic parity 0, 0 copper errors, 230 unconnected, 19 starved thermals (new buck pads + J201 GND).
- All parts are placed. Copper is only the scripted part: critical routes, power pours, via arrays. Most signals are not routed.
- Scripted pipeline (`bl/`, run with KiCad CLOSED, pcbnew python `~/.cache/mark-mods/kicad-mcp-big-venv/bin/python`):
  - order: `newplace.py` -> `buckplace.py` -> `critical.py` -> `pours.py` -> `fill.py`;
  - `bl/place_tools/pipeline.sh <board> <logdir>` runs all five steps;
  - re-runs are idempotent.
- Reports in this folder:
  - removal and additions: `esp_removal_report.md`, `additions_report.md`;
  - bucks: `tps54360_report.md`, `lm70880_report.md`, `lm70880_thermal_7a5.md`;
  - placement: `placement_report.md`.

## Placement experiments (2026-10-25)
- **Whole-board KRT placer: no-go.**
  - Seeds failed 82-97 nets with floorplan errors; our placement failed 87 with the same quick-route judge.
  - Recurring failures on every seed: IMU_INT1, VCAP2, DRV DVDD. That is STM32/DRV congestion.
- **Power-right / logic-left split.**
  - Our blocks act as rigid templates; KRT `place_simple` places the rest.
  - Results: `split_trial/` in this folder (copied from the session scratchpad when done): `REPORT.md`, `floorplan_rules.md`.
  - If it beats 87 clearly:
    1. Owner checks the terminal positions (mechanical).
    2. Rewrite our scripts to `floorplan_rules.md`.
    3. Build the In2 split: +BATT/VBUS under power, +3V3/+5V under logic.

## Next steps
1. Decide split vs current placement (see `split_trial/REPORT.md`).
2. STM32 pin-swap study: assign pins to match the DRV sides. Needs owner OK (firmware pin map).
3. Route: our scripts, then KRT `route.py` or Freerouting.
   - Run the `diagnose-routing-failures` skill after each run.
   - Finish with `review-routed-board`.
4. Before fab:
   - D2 input TVS clamp (~69 V) vs 65 V parts;
   - J510 solid connection + outer +24V pour;
   - Kelvin net-ties on the shunts;
   - Degson spacing;
   - D902 copper (~1.3 W);
   - J1 solid In2;
   - JLC BOM. J510 has only 197 in stock; SR2512 7.5 R only 863.

## Rules
- No git commits; the owner reviews and commits.
- KiCad CLOSED for every file write; check `pgrep -x kicad/pcbnew/eeschema`. Never let an open editor save over file edits.
- Use kipy/IPC on an open editor, never desktop screenshots.
- RAM: keep the whole machine under ~27 GB (baseline ~13 GB). Put parallel heavy jobs in ONE `systemd-run --user --scope -p MemoryMax=<27-used>G -p MemorySwapMax=0` scope.
- KRT placer: use the cores for more seeds (16 at `--jobs 16`), then judge 6-10 in parallel.
- KRT tools:
  - always `--no-fix-drc-settings`;
  - KRT root `~/Documents/abx-motion-routetest/tool/KiCadRoutingTools`, venv `~/Documents/abx-motion-routetest/tool/venv`;
  - never run the stress-test-router skill (it files GitHub issues).
- Agents:
  - fresh, small, effort high, model not set;
  - hand-backs of 15 lines or fewer, plus a report file;
  - work on copies first, back up before touching the real board;
  - verify their ERC/DRC claims yourself.
- Owner style: terse, recommendation first, best practices by default, confirm before big redesigns.
