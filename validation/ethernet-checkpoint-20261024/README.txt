ABX-Motion-ETH Rev1.2b final QA of the initial routing checkpoint
2026-10-24 | Reviewed design commit49651c5

RESULT: suitable for publishing as an in-progress development checkpoint.
NOT a completed Ethernet implementation or manufacturing release.

Fresh native KiCad10.0.7 checks:
- Schematic ERC:0 violations.
- PCB, with refilled zones, all-track-errors and schematic parity:
  0 unconnected items among defined nets.
  0 copper shorts, copper clearance, drill-clearance or track-crossing violations.
  49 parity warnings, exactly the declared unintegrated Ethernet footprints.
-12 converter footprints are integrated and match the freshly exported netlist.
- Every other schematic-mapped PCB pad also matches that netlist.
- Approved placement/rotation and original pad nets are preserved.
- Original zone assignments and ground-plane routing are preserved.
- Root Rev1.2a PCB/schematic hashes are unchanged.
- All61 new parts remain excluded from BOM/CPL.
- All referenced 3D model files resolve. Native top render inspected.
- ETH project minimum copper clearance and track width remain0.15mm.

Remaining154 DRC findings:
  42 dangling-via;37 dangling-track;26 solder-mask bridge;
  19 footprint-library mismatch;17 silkscreen overlap;13 silk over copper.
The26 solder-mask reports reference the existing rear ESP TIM opening and GND
pad/zone geometry. They remain recorded for explicit release disposition.
Dangling thermal/stitch/power copper was not indiscriminately deleted.

Release gates: integrate/routethe49 remaining Ethernet parts; verify magjack
isolation/return paths/actual impedance stack; resolve/disposition DRC findings;
review BOM/CPL and prototype electrical/thermal/firmware performance.
Zero defined-net opens does not imply Ethernet is functional.

Artifacts: board-drc.json, schematic-erc.json, netlist.xml, qa-summary.json,
top.png. audit.py independently checks against the approved placement commit.
Unrelated local root .pro/.prl edits are excluded from this checkpoint.
