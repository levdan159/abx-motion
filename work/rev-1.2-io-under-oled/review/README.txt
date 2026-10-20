REV 1.2-dev — DIGITAL I/O UNDER OLED / VERTICAL CONNECTOR BANK
Active files: root abx-motion.kicad_pcb and MCU.kicad_sch.
Baseline: local commit 673dc00. Rev 1.2 remains local development.

Placement
38 low-profile parts (PCA9555, RC filters, output switches, fuse and related
passives) now occupy the existing OLED outline. OLED header and mounting holes
retain their locations. A 3 mm radial mounting-post reserve is clear of these
components. Six original JST-PH connectors are rotated 90 degrees, arranged as
two columns by three rows below the display. Front/rear names and pin legends
follow actual pads; back text is mirrored. All pin/net mappings and values
remain unchanged. The connector row order is M1/M2 limits, S1/S2 limits, OUT1/2.
Four dual limit ports still provide eight inputs; two ports are switched outputs.

Measured reclaimed space: X80.5..92.1, Y109..140 mm is free of component
footprint envelopes: 11.6 x 31 mm, about 360 square mm. Copper still traverses
this region; it is available for a later placement/routing pass, not an assigned
keepout or a promise that the complete three-axis driver design fits there.
207 other footprints retain position, orientation, footprint and pad geometry.
Existing relay bay, motor bridges and upright EXT/motor connector bank preserved.

OLED stack
Updated requirement is 10 mm PCB-to-PCB spacing with direct plug-in.
J208 development selection: Samtec SLW-104-01-L-S low-profile 4.57 mm socket.
OLED-side mate: MTSW-104-07-L-S-215, 5.461 mm mating post and 2.54 mm insulator.
Nominal engagement at 10 mm spacing: 5.461 - (10 - 4.57 - 2.54) = 2.571 mm.
SLW allowed insertion is 2.16..2.92 mm. No shims specified. Check the full
tolerance stack and actual engagement during module selection/assembly. Header
seating and actual spacer dimensions matter; this is nominal, not a qualified
mechanical stack. Socket footprint uses 0.9 mm finished holes (vendor layout
recommends 0.86 mm), original pad centres, 1.7 mm pads and unchanged pin order:
1 GND, 2 +3V3, 3 SCL, 4 SDA. Do not substitute a differently ordered OLED.
The custom VRML is a dimensional socket envelope, not a vendor STEP or an OLED
module model. Socket needs exact supply/assembly confirmation before release.
The exact OLED remains unspecified: its outline, hole pattern, underside parts,
header polarity and dimensional tolerances must be matched before manufacturing.
The 0.96/1.3-inch label was never proof of universal module compatibility.

Routing
Automatic A* through pcbnew, geometry-checked fanouts, native zone refill and
KiCad DRC were used. New routes were simplified to straight runs and 45-degree
bends where clearance allows. Two polish passes removed 465 unnecessary
segments; obsolete local tracks and unused vias were pruned afterward.
Most new routing is on F.Cu/B.Cu; congested low-current links also use In2.Cu.
The long STEP2 enable connection was moved back to outer layers; only a 0.215 mm
In2 attachment remains for it. No new tracks on the In1 ground reference plane.
Audit JSON lists new inner-layer lengths. Original zone boundaries/nets remain
unchanged and the filled zones pass connectivity DRC. A low-current pull-up
branch uses 0.15 mm track (existing allowed minimum); power/motor widths and
rules are unchanged. Added vias are tented; retained original via tenting restored.
No component values, circuitry, current targets or protection settings changed.

Validation
Final KiCad DRC: 0 errors, 0 unconnected items, 0 schematic parity issues.
Only the 19 pre-existing library-footprint warnings remain; no dangling tracks,
dangling vias, silkscreen or courtyard warnings remain. ERC: 0 violations.
Electrical netlist matches the prior 751-pin netlist. All 20 thermal-improvement
vias and all 337 protected production files are preserved. Original unrelated
routing is retained; the audit records exact modified/removed/new object counts.
No powered or physical thermal/mechanical tests are implied by these checks.
placements-native.csv uses KiCad native coordinates/rotations, not JLC CPL
corrections. Existing production exports continue to describe Rev 1.1d.

Review files
front.png / back.png: final native 3D previews (display module omitted).
audit.py / audit.json: reproducible checks against Git baseline 673dc00.
drc.json / erc.json / netlist.xml: final native electrical validation.
changes.json, collision-ripup.json, fanout.json, repaired-fanout.json,
straightening.json, step2-straightening.json, cleanup.json,
inner-route-reduction.json: bounded change records. Intermediate routing search
scripts/checkpoints are not a supported rebuild pipeline; do not run legacy
project-wide scripts over this board. Final native PCB is authoritative.

Primary manufacturer references checked 2026-10-21
https://www.nxp.com/docs/en/data-sheet/PCA9555.pdf
https://www.samtec.com/products/slw-104-01-l-s
https://suddendocs.samtec.com/catalog_english/slw.pdf
https://suddendocs.samtec.com/prints/slw-1xx-01-x-x-footprint.pdf
https://www.samtec.com/products/mtsw-104-07-l-s-215
https://suddendocs.samtec.com/prints/mtsw-xxx-xx-x-x-xxxx-xx-xxx-mkt.pdf
