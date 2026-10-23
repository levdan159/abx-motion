ABX-Motion Rev 1.2a — JLCPCB prototype fabrication / assembly review package
2026-10-23

UPLOAD MATCHED FILES ONLY
abx-motion-rev1.2a-gerbers.zip + abx-motion-rev1.2a-jlcpcb-bom.csv + abx-motion-rev1.2a-jlcpcb-cpl.csv
74 catalogue SKUs / 328 placements; J208 and mechanical items are separate.
No Ethernet or PoE circuitry is present.

PCB ORDER
Four layers in order: F.Cu, In1.Cu (GND), In2.Cu, B.Cu. FR4, 1.6 mm finished thickness, 35 um copper each layer, green mask, white silk, ENIG for exposed gold artwork/TIM contacts.
Gerber and drill origin: absolute KiCad origin; CPL X is native X, CPL Y is negative native Y (positive upward), units mm. No mirroring of top placements. Negative Y coordinates are intentional. Do not independently offset CPL and Gerbers.
Epoxy resin-filled, planarized and copper-capped thermal holes (IPC-4761 Type VII / JLC POFV), both faces, per filled-capped-vias.csv (104 features). This includes the twelve explicitly listed ESP exposed-pad thermal holes, not insertion holes. Do not fill actual connector, lead-insertion or mounting holes. Confirm the fab can apply this distinction to thermal PTH features and provide at least 25 um finished barrel copper for the thermal model assumption.
Top stencil only for component assembly. Back mask openings are TIM contact areas, not paste pads. Retain the segmented driver EP stencil. Request X-ray inspection of all three driver exposed-pad joints; target <=20% void area with no large central void, subject to agreed assembler acceptance.

ASSEMBLY CHECKS / UNRESOLVED ITEMS
Supplier numbered pad centers were fitted and checked against corresponding native PCB lands for every catalogue placement. Derived rotations/origins are in placements.csv/json. These are catalogue-geometry checks, not physical supplier fit approval.
K501/K502: C116963 supplier CAD COM-to-coil-row offset differs from Omron's drawing by about 0.55 mm. Rotation/pin numbering is identified, but supplier-model origin cannot be certified from that inconsistent geometry. JLC must align actual G5LE-14 5 V relay using the manufacturer hole drawing and PCB lands before assembly. Do not move PCB holes to match the malformed supplier model. See assembly/relay-alignment.svg and assembly/placement-overlays.html. CPL contains the best fit to supplier numbered pads, explicitly subject to this correction.
J208 is the separate low-profile Samtec socket in manual-and-mechanical-bom.csv. Do not let BOM matching substitute a generic tall socket. Its actual OLED/header stack must engage correctly at the required 10 mm standoff height.
Through-hole headers, JST connectors, terminal blocks, relays, capacitors and fuse holder require the applicable selective/wave/manual assembly process. Check service availability/fixtures with JLC; SMT-only assembly does not fit these automatically.
Catalogue identity and advertised package/specifications verified against retrieved JLCPCB pages. JLC and LCSC inventory differ; listing is not stock reservation. Confirm exact MPN availability and quantity, including assembly overage, during quotation. No part substitutions have been silently applied.
No upload, order, purchase or supplier message was performed.

STATUS
ERC: zero violations. DRC: zero errors, zero unrouted connections, zero schematic parity issues; 95 warnings remain (51 dangling via, 17 dangling track, 19 library mismatch, 7 silk overlap, 1 silk over copper). No electrical routing or component placement was changed for the revision/branding/metadata export work; only decorative badge placement changed.
This package supports prototype fabrication and assembler review. It is not a qualified continuous-current/thermal/fault release. Motor, thermal, regenerative-energy and fault tests require hardware and have not been run. Standardised current ratings cannot be inferred from the chip package limit or 25 A label.
Cooling direction: stock underside finned sinks plus supplemental top-side sinks. Exact parts/retention/performance pending; archived machined HS1 drawings are superseded and are not assembly instructions. Do not operate drivers at high current without a completed cooling assembly.

Official format/process references:
https://jlcpcb.com/help/article/advice-for-bom-and-cpl-files-preparation
https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly
https://jlcpcb.com/help/article/pcb-via-covering
https://www.samtec.com/products/slw-104-01-l-s
https://components.omron.com/us-en/products/relays/G5LE
