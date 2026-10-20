REV 1.2-dev — LOW-PROFILE EXTERNAL STEPPER CONTROL HEADERS
Active files: root abx-motion.kicad_pcb, Steppers_Relays.kicad_sch,
abx-footprints.pretty/EXT_Header_1x04_P2.54mm_RightAngle.kicad_mod.

J502/J504 are now unshrouded right-angle 1x4 male headers, mating outward at the
bottom edge. Reference physical part: Wurth Elektronik WR-PHD 61300411021.
The row remains at Y148 with original pin-1 X positions 96 and 124 mm.
Pitch changes from JST-XH 2.50 to 2.54 mm; pad 4 moves +0.12 mm in X.
Pads remain 1.7 mm, with 1.1 mm drills matching the manufacturer recommended hole.
Pin order is preserved: 1 EN (gated), 2 STEP, 3 DIR, 4 GND. Pin 1 is rectangular
and has a silk L marker. Both front and rear pin labels were repositioned at new
pad centers and expanded to EN / STEP / DIR / GND; rear labels are mirrored.
Each connector reference is centered over the new row. J501/J503 remain JST-XH.
The headers are unkeyed; use the printed pin-1/signal markings when wiring.

Footprint derived from installed KiCad PinHeader_1x04_P2.54mm_Horizontal:
reversed row coordinate/numbering allows outward bottom-facing pins while keeping
pin 1 left in the top view. The symmetric generic 3D model has corresponding
7.62 mm Y offset. Board rotation is 270 degrees. Off-board metal-pin drawings
are on fabrication, not silkscreen. Plastic body stays inside the board edge;
mating pins intentionally project about 5 mm outside it.

Only these two footprints and their front/rear labels changed. All 250 other
footprints and all 2949 tracks/vias are unchanged. No rerouting needed: existing
endpoints remain inside the new lands. Electrical netlist unchanged.
DRC: 0 errors, 0 opens, 0 parity issues, 19 existing library warnings only.
ERC: 0 violations. All 337 production files are byte-identical.

Schematic and PCB contain matching hidden manufacturer/MPN/datasheet fields.
Rev 1.2 procurement override is design/rev-1.2-parts-overrides.csv. No JLCPCB stock
part has been selected for the new headers. Existing Rev 1.1d BOM/CPL/Gerbers
remain the old release; do not use them as Rev 1.2 assembly metadata.
No Rev 1.2 manufacturing package generated. Work stays local.

Primary sources checked 2026-10-20:
https://www.we-online.com/components/products/datasheet/61300411021.pdf
https://www.we-online.com/en/components/products/BTB_WR_PHD_2_54_MM_PIN_HEADER_SINGLE
Manufacturer PDF was search-index readable; direct full PDF retrieval was blocked
by the source. Generic model is representative, not a supplier-specific STEP.

Implementation steps are recorded in implement.py then finish.py. Do not rerun
over later PCB edits. audit.py validates the final scope and front/rear labels.
