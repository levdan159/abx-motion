Root ABX-Motion Rev1.2b DRC cleanup —2026-10-24
Baseline commit:41f87bf

FINAL RESULT
0 DRC violations (all severities, including exclusions, all-track-errors).
0 unconnected items on defined nets.
0 schematic-parity issues.
0 ERC violations.
No DRC rules were relaxed, findings excluded or severity levels disabled.

CHANGES
- Removed157 redundant copper objects (104 tracks,53 vias), trimmed dangling
  tails at their valid junctions and made explicit centerline connections where
  old routes met only at copper edges.14 replacement/connection tracks were added.
- Verified native connected pad groups before/after cleanup. All original pad
  numbers, net assignments, positions, shapes, drills and layer sets are preserved.
- All original component positions, GND vias and zone boundaries are preserved.
- Replaced the unassigned ESP rear mask rectangle with a GND-assigned4x4mm
  copper/mask pad; no paste opening. Original ground thermal vias retained.
- Routed /M1_PWM_PH around that thermal area, removing exposed signal copper.
- Relocated reference text/legends; trimmed one crystal silk edge; narrowed the
  back legend frame to clear the RJ45. Aligned rear revision text to1.2b.
- Saved18 reviewed custom footprint definitions and synchronized16 schematic
  symbol definitions. Existing pad geometry/model transforms were preserved.
-49 unintegrated Ethernet placement reserves are now explicitly board-only
  (Not in schematic). This matches their actual CAD state and protects them
  during schematic updates. They remain net0 and excluded from BOM/CPL.

IMPORTANT SCOPE
A clean DRC is for the currently integrated draft only. The49 Ethernet reserves
are NOT electrically integrated or routed. No new Ethernet functional claim,
manufacturing package, BOM/CPL release or hardware qualification is provided.
Future schematic integration must clear board-only on each newly linked part.

EVIDENCE
final-drc.json, final-erc.json, netlist.xml, qa-summary.json.
audit.py checks immutable baseline geometry/nets/connectivity and unchanged
project rules. top.png and bottom.png are native root-project renders inspected
for placement, thermal window and legend appearance. The model paths still
resolve from the project-local Ethernet model bundle.

The active files remain abx-motion.kicad_pro / .kicad_pcb / .kicad_sch in root.
Local UI state (.kicad_prl) was not staged. The variant folder remains an earlier
review snapshot; root is the current working project.
