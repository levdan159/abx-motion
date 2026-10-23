ABX-Motion-ETH — proposed Rev 1.2b Ethernet assembly option
========================================================

OPEN THIS BOARD FOR THE PLACEMENT REVIEW:
  abx-motion-eth-placement.kicad_pcb
  abx-motion-eth-placement.kicad_pro

This is a PHYSICAL PLACEMENT STUDY, not an electrically integrated PCB or a
manufacturing release. The root Rev 1.2a PCB, schematics and production exports
have not been changed. This directory intentionally has no schematic claiming
that the proposed Ethernet circuitry has already been wired.

PRODUCT IDENTIFICATION
PCB hardware revision: Rev 1.2b, once the electrical design is finalized.
Base assembly SKU: ABX-MOTION.
Ethernet assembly SKU: ABX-MOTION-ETH.
An order/stock record can append revision: ABX-MOTION-ETH-R12B.
Use Rev 1.2b on the PCB; record fitted Ethernet as the assembly option. Avoid
1.2b.e as a revision identifier because it combines hardware revision and option.
The intended common bare PCB could be assembled with Ethernet omitted; that
population option and any required links/firmware changes remain to be defined.
The Rev 1.2a PCB cannot gain Ethernet merely by changing its assembly BOM.

PLACEMENT PROVIDED
- J801: HR911105A, JLC C12074, opening toward the top board edge. Body envelope
  x112.54..128.58 / y45.99..67.29 mm. Board top edge y48.00 mm, giving 2.01 mm
  front overhang. Nominal height 13.5 mm. Verify actual drawing/panel latch access.
- U801: W5500, JLC C32843, at (120.3,74.8), rotated 270 degrees to put its
  Ethernet MDI pin bank toward the jack. Crystal immediately below its clock pins.
- 42 new footprint positions cover controller, jack, clock, bypass/bulk caps,
  reference termination network, straps, reset/interface and ESD package reserves.
- Existing 5 V converter, inductor, 3.3 V regulator, ADC divider and their support
  parts retain their original positions. The five rail/ground test pads form one
  row to the right of the RJ45. CS1 and CS2 sit to the left of the ESP32, at
  (82.5,51) and (88,51) mm, rotated 90 degrees, with front/back legends above.
  Three existing pull-ups move below/right of the PHY. These are the only ten
  existing footprint moves relative to Rev 1.2a.
- The stepper/watchdog IC positions, motor sockets and board outline are retained.
- A 16.5 x 4.5 mm dedicated Ethernet supply reservation is marked on Dwgs.User.
  It is NOT a selected/connected regulator or a demonstrated complete supply fit.
- No PoE circuitry or PoE connector claim is included. HR911105A is non-PoE and
  rated 0..70 C; broader temperature/PoE variants need a new connector selection.

CHECKS AND LIMITS
- Geometry review: no courtyard intersections involving the new/moved parts.
- USER UPDATE: the additional 15 mm antenna clearance was explicitly waived to
  simplify integration. J801 now enters that former clearance envelope; other
  proposed Ethernet footprints remain outside it. Nominal body-to-module lateral
  gap is 2.54 mm, with no footprint courtyard intersection. This is a geometric
  screen, not measured RF qualification. Wi-Fi range/throughput may suffer and
  must be measured with the real jack, plugged cable and enclosure.
- All original segment, via and zone expressions are retained verbatim. No
  necessary original trace has been deleted to make the placement look clear.
  CONSEQUENCE: old copper remains at the pre-move test-pad/pull-up positions; it
  is not valid routing for those moved parts and conflicts with proposed pads.
  Filled copper also remains under the proposed jack. It must be cleared/rerouted
  with reviewed keepouts during electrical integration; DO NOT fabricate this file.
- Every new footprint is excluded from BOM and CPL. Pads have no assigned nets,
  and the new references are not present in the schematic. This prevents the
  placement study being mistaken for a completed assembly export.
- U803, Q801 and D801 are provisional package allocations, not frozen MPNs.
  Crystal CL/load caps, protection ratings, jack pinout/center-tap network and
  regulator selection still require electrical review. Some package choices can
  change after that review, so this is not a promise that routing will be complete.
- W5500 pin 18 VBG is intentionally left floating in the circuit proposal;
  C809 is 4.7 uF for TOCAP pin 20, C810 is 10 nF for 1V2O pin 22.
- Schematic ERC, PCB parity, DRC and zero-open release checks have NOT passed for
  this study. They apply after the circuit is actually integrated and routed.

NEXT ELECTRICAL CHECKPOINT
1. Freeze the Ethernet power source. The existing AP2112 is a thermal/current
   constraint. The previous full-allocation analysis already exceeded the old
   2 A main-buck capability; do not assume a new 5 V-fed LDO has spare capacity.
   Preserve the intended 1 A external 5 V allocation. A dedicated protected-VBAT
   3.3 V buck is an option, but requires checking independent power sequencing,
   USB-only behavior and SPI/reset back-powering before adopting it. LMR36506R3
   has a compact 65 V/600 mA option; the reserved box is not its completed layout.
2. Confirm shared SPI/polling behavior and GPIO3 boot-state allocation; move the
   status LED to an expander output and provide an expander reset interface.
   U601 pads 18/19 currently have GND ties that MUST be removed before reuse.
3. Build and check the Ethernet schematic using the exact jack transformer/LED
   diagram and selected supply/protection/reset parts. Reconcile actual parts
   and footprints with the reservation before touching routing.
4. Preserve the existing supply hot-loop/feedback/thermal layout. Review new
   Ethernet supply copper separately. Remove only identified obsolete/conflicting
   copper in a separate reviewed routing operation.
5. Integrate, route and validate, then create separate base/ETH assembly BOMs,
   supplier-checked CPL rules and matched manufacturing packages.

VIEWS AND EVIDENCE
  layout-review/placement-detail.png   Annotated close placement view
  layout-review/placement-overview.png Whole-board placement view
  layout-review/placement-3d.png       Mechanical visualization
  layout-review/geometry.json         Courtyard/antenna screen
  layout-review/parts.json            New package positions and unresolved status
  layout-review/moved-parts.json      Exact 10-part existing placement changes
  layout-review/preservation.json     Source/copper preservation evidence

The local RJ45 VRML is an approximate, dimensioned mechanical envelope with a
visible mouth, not a vendor STEP model or authority for supplier CPL rotation.
Other local visualization models are copied from the Rev 1.2a project.

Baseline commit: ce34a43.
Date: 2026-10-23.
Build/review scripts: work/ethernet-rev1.2b-20261023/placement.py and review.py.

PRIMARY DESIGN REFERENCES
https://docs.wiznet.io/Product/Chip/Ethernet/W5500/ref-schematic
https://docs.wiznet.io/Design-Guide/hardware_design_guide
https://jlcpcb.com/partdetail/Wiznet-W5500/C32843
https://jlcpcb.com/partdetail/C12074
https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html
https://www.ti.com/product/LMR36506
