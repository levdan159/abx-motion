2026-10-24 Ethernet cleanup and routing checkpoint

Current deliverable: variants/ABX-Motion-ETH/abx-motion-eth-placement.kicad_pcb
Source placement checkpoint: commit 9fd9be1. The before/ copy is local recovery.

Accepted sequence:
  power_schematic.py -> exported with-power-netlist.xml / zero-violation ERC
  clean_and_integrate.py -> cleanup.json
  route_power.py -> power-routes.json (68 segments, 17 vias)
  purge_padless.py -> padless-removals.json
  restore_connections.py pass1, pass2 -> restoration-added-pass*.json
  ESP TIM crossing I2C_SDA candidate removed; rerouted outside thermal opening
  R747 local GND via at135.9,82.2 (0.6mm copper /0.3mm drill)
  final_signal_cleanup.py ->34 redundant signal objects removed
  final-drc.json ->0 opens,0 shorts/clearance/drill/crossing errors
  final-erc.json ->0 violations
  review_progress.py ->actual copper previews and preservation checks

Scripts are checkpoint-specific audit aids, not idempotent general tools.
Do not rerun historical generators over the routed deliverable.
Some helper imports use existing local work/ scripts; the PCB/schematics are the
reviewable deliverables and do not need those generators to open in KiCad.

The initial manual restore_power_taps trial was rejected and reverted; its
local artifacts are NOT accepted evidence. Power-first DRC is superseded by
power-second DRC. Current evidence is final-drc/final-erc and routing-progress.

All61 Ethernet option footprints remain excluded from BOM/CPL. Only12 supply
footprints are schematic integrated;49 remaining Ethernet circuit footprints
have no nets yet. Zero defined-net opens does NOT mean Ethernet is complete.

Remaining DRC flags:37 dangling tracks,42 dangling vias,26 ESP rear TIM aperture
reports against GND pads/zone,19 library mismatches,17 silkscreen overlap,
13 silkscreen-over-copper. Thermal/plane/motor stitching copper was not swept
just to clear these reports. Entire draft requires further release review.

Root Rev1.2a PCB and six schematic hashes match the immutable baseline.
No PoE, manufacturing exports, MCU GPIO reassignment, or new jack isolation
qualification is included in this checkpoint.
