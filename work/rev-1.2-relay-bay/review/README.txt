REV 1.2 DEVELOPMENT — RELAY BAY CONSOLIDATION
Root abx-motion.kicad_pcb and six schematics now contain this development revision.
Rev 1.1d release remains in production/rev-1.1d-20261020. No production exports were changed.
Branch stays local, per user instruction. This is not a manufacturing release.

Implementation
Retained both G5LE-14 5 V relays and all component values. Moved 14 relay-bay parts;
rotated K502 horizontally. Both relay-output connectors remain fixed.
Reconnected all relay nets using local routing only, 0.8 mm contact tracks,
0.25 mm coil/control and 0.4 mm shared supply/GND additions. Contact routes have
no added vias. No new signal routing on inner planes.
238 other footprints preserved, including power, MCU, existing steppers and thermal design.
2720 original tracks/vias preserved; 102 local items removed, 359 local items added.
The original remaining track geometry and net assignments were independently compared.
Electrical netlist is identical to the validated Rev 1.1d thermal netlist.
Design-rule settings unchanged. All 337 protected production files hash-identical.

Space
Fixed inspection region X136..157, Y104..119.5 mm. At 0.1 mm sampling with 0.25 mm
margin around physical footprint bounding boxes, largest empty rectangle increased
from 21 x 2.2 mm (46.2 mm2) to 21 x 9 mm (189 mm2).
This is component space, not a copper keepout. Future integrated driver circuits
still require complete thermal, routing, decoupling and mechanical design.

Bounded relay comparison
G5Q-14 DC5: smaller, but standard DC resistive contact rating lower than G5LE;
G6RN-1 DC5: narrow, but 5 A / 30 VDC resistive lower than baseline;
G6C-21: separate NO and NC contacts, not equivalent common-pole SPDT.
Therefore retained original G5LE and consolidated placement instead of reducing capability.
G5LE standard DC rating is 8 A / 30 VDC resistive, 4 A / 30 VDC inductive;
10 A carrying/AC figures do not establish 10 A DC switching. 32 V load switching
still requires qualification for the actual load. Existing assembly alignment
review remains relevant; no new manufacturing CPL is issued for Rev 1.2-dev.
Sources:
https://omronfs.omron.com/en_US/ecb/products/pdf/en-g5le.pdf
https://omronfs.omron.com/en_US/ecb/products/pdf/en-g5q.pdf
https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6rn.pdf
https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6c.pdf

Validation
root-drc.json: 0 errors, 0 opens, 0 schematic parity issues;
19 pre-existing library footprint mismatch warnings, no new warnings.
root-erc.json: 0 violations.
Native placement CSV is a review document, NOT JLCPCB CPL.
No physical motor, fault or thermal qualification was performed.
Legacy rebuild scripts must not be run on this manually placed revision.
Audit-scope-before-promotion.py intentionally requires unchanged baseline root hashes;
it is evidence of the pre-promotion check, not a post-promotion updater.
