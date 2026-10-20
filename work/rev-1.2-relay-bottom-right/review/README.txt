REV 1.2-dev — BOTTOM-RIGHT RELAY CONNECTORS AND LED POLISH
Active design: root abx-motion.kicad_pcb. Baseline: local commit b645799.
This remains development work, not a manufacturing release. No push.

User-selected constraints
Both J505/J506 remain bottom facing. Motor 2 components, routing and thermal
features are preserved. Both relay-output connectors move right: J505 +17 mm X,
J506 +15.25 mm X, with unchanged Y and orientation. K501 moves down 10 mm;
K502 is rotated to put the pins in a more useful location, with its body about
0.5 mm higher to leave a readable connector pin-label strip.
Motor 2 capacitor and fault/snubber parts remain at their original locations.
Bottom-right connector courtyard clears the mounting-hole courtyard by ~0.54 mm.

Indicators and legends
D502/D504 are above their respective relay circuits. RLY1 ON and RLY2 ON indicate
coil drive; they do not sense mechanically closed contacts. Stale freestanding
RLY labels were removed. Front/rear J505/J506 pin labels match actual pads:
1=NO, 2=COM, 3=NC. Rear legends sit below pins to avoid the copper branding.

Routing
Rebuilt relay-private circuits and affected +5V/GND/control branches only.
Six 0.8 mm contact paths use 18 straight/45-degree track segments total, no vias.
Coil/control tracks 0.25 mm; added shared supply/GND branches 0.4 mm.
Back copper logo was included as a routing obstacle. In1/In2 signal tracks were
not introduced. Copper zone boundaries/nets remain unchanged; pours refilled.
Removed two unused vias and merged collinear new-route segments.

Scope and checks
16 footprints moved, 236 untouched. Pad sizes/drills/pin nets and part values
unchanged. 2718 retained tracks/vias identical to the baseline. Removed 361 local
items and added 231 local items. All 20 prior thermal-improvement vias preserved.
All 337 protected manufacturing files remain hash-identical. Electrical netlist
identical to Rev 1.1d validated netlist.
DRC: 0 errors, 0 opens, 0 schematic parity issues; 19 existing library warnings.
ERC: 0 violations. No silkscreen, courtyard, dangling-track or dangling-via warnings.

Space comparison
Same inspection ROI X136..157, Y104..129.5 mm, 0.1 mm grid and 0.25 mm margin around
physical footprint envelopes: largest component-free rectangle increases from
21 x 9 mm (189 mm2) to 16.1 x 16.9 mm (272.09 mm2), approximately 44% more area.
This describes component envelopes, not a copper keepout or a fully allocated
three-axis driver circuit. Existing StepStick parts remain in place.

Native-placement-changes.csv is a review table, not a JLCPCB CPL. Rev 1.1d release
exports remain untouched; eventual Rev 1.2 release will require fresh placement
metadata and assembly review for the new relay locations/orientation.
Scripts record bounded implementation steps, not a general project rebuild.
Do not rerun placement/routing scripts over later edits.
