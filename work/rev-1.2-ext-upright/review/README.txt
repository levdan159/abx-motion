REV 1.2-dev — UPRIGHT EXT HEADERS, RIGHT-PACKED CONNECTOR BANK
Active design is the root PCB and schematic. Baseline local commit 2fe3a7b.
This supersedes the right-angle pin option. No pins extend beyond the board edge.

Final physical arrangement
J501 motor 1: pin 1 X96.5, Y148; unchanged JST-XH part and pin order.
J502 EXT1: X111.3, Y140.9; upright 1x4 2.54 mm header, row runs along +Y.
J503 motor 2: pin 1 X118.2, Y148; unchanged JST-XH part and pin order.
J504 EXT2: X133.0, Y140.9; same upright header.
Each JST-to-EXT courtyard gap is 2.53 mm. J501 was shifted another 1.3 mm right
for symmetry. JST origins are 21.7 mm apart (previously 28 mm). Compared with
the original bank, the left physical envelope moved right 14.5 mm and the bank
is 13.12 mm narrower. Header bodies and pads remain within board outline.
R507 moved from Y141 to Y137 to clear J502. No other circuit topology changed.

Headers and legends
Reference part Wurth Elektronik 61300411121 (straight THT WR-PHD, 1x4, 2.54 mm).
Custom footprint is the installed KiCad vertical pin-header footprint with 1.1 mm
drills. Generic upright STEP model; no body/pin offset. Pin 1 rectangular.
Pin order from the inner end toward the bottom edge: 1 EN, 2 STEP, 3 DIR, 4 GND.
Front and rear signal legends follow the actual pad coordinates. Rear text is
mirrored. J504 legends are rotated to fit the clear strip beside the relay.
JST motor pin legends and references moved with the connectors on both sides.
Q503 reference moved for readability; Q503 component position remains unchanged.
Schematic and PCB procurement fields agree; parts override lists the straight MPN.

Routing and validation
Affected connections were routed automatically with A* through pcbnew, retaining
F.Cu/B.Cu only. No new inner-plane signal tracks. All eight motor coils use at
least 0.5 mm traces; required layer transitions use tented 1.0 mm / 0.5 mm vias.
The four Motor 1 nets were routed again automatically after the symmetry shift.
Local enable/pull-up and button-trace branches were reconnected around the new
holes. Obsolete traces/vias were pruned to connection points, then zones refilled.
No remaining dangling-track/via or silkscreen/courtyard warnings.
DRC 0 errors, 0 opens, 0 schematic-parity issues; 19 existing library warnings.
ERC 0 violations. Electrical netlist unchanged. All 20 thermal-improvement vias
and original copper-zone boundaries/nets preserved. All 337 manufacturing files
remain byte-identical. Audit JSON gives exact final scope and track counts.

The upright headers use different cables from the old 2.50 mm JST-XH EXT parts.
They are unkeyed; follow printed signal/pin-1 markings. J501/J503 remain keyed JST.
Existing production exports describe Rev 1.1d. This is local Rev 1.2 development,
not a new manufacturing release; future assembly release needs new CPL/BOM.
Native placements are not JLCPCB placement corrections. No branch push performed.

Primary manufacturer reference:
https://www.we-online.com/en/components/products/BTB_WR_PHD_2_54_MM_PIN_HEADER_SINGLE
https://www.we-online.com/components/products/datasheet/61300411121.pdf
Implementation scripts record bounded steps and intermediate proposals. Do not
rerun them over later PCB edits. The root PCB and audit.json are the final state.
