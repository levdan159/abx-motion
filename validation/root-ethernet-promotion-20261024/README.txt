Root abx-motion promotion from the reviewed Rev1.2b Ethernet draft
2026-10-24

The active root files are abx-motion.kicad_pro, abx-motion.kicad_pcb and
abx-motion.kicad_sch with their hierarchical sheets and local libraries.
The PCB is byte-identical to the reviewed variant; no copper was edited here.
Schematic instance project names and project metadata were changed to abx-motion.
New footprint/symbol libraries and two envelope models were installed in root.

Fresh checks after promotion:
- ERC:0 violations.
- Defined-net opens:0.
- Copper shorts / clearance / drill clearance / crossings:0.
- Schematic parity:49 expected draft Ethernet footprints, unchanged.
- All schematic-mapped PCB pads match the fresh root netlist.
- All referenced 3D model files resolve from root.
- Existing154 DRC findings remain identical to the reviewed source checkpoint.
- Project minimum clearance and minimum trace width are both0.15mm.

This is a DEVELOPMENT DRAFT, not a manufacturing release. The49 draft Ethernet
footprints still need schematic integration and routing. Manufacturing exports
from Rev1.2a are historical and do not describe the root Ethernet draft.

Rollback: root CAD before promotion is in Git commit86024cc. Original local
project settings, including the pre-existing .pro/.prl edits, are also preserved
under work/root-ethernet-promotion-20261024/before/. The .prl was not overwritten.

Open/reload abx-motion.kicad_pro from root to view the updated project.
Artifacts: erc.json, drc.json, netlist.xml, qa-summary.json; audit.py verifies
root/source equivalence and root-relative dependency resolution.

Follow-up: project-local Ethernet model paths were added after promotion. The
audit normalizes model filenames when comparing source/root PCB data; all
geometry, electrical data and assembly attributes remain identical. See
../root-model-fix-20261024/ for the model-only diff check and fresh render.
