ABX-Motion-ETH — proposed Rev 1.2b Ethernet assembly option
========================================================

OPEN THIS BOARD FOR THE ROUTING REVIEW:
  abx-motion-eth-placement.kicad_pcb
  abx-motion-eth-placement.kicad_pro

ROUTING IN PROGRESS, not a manufacturing release. The variant now has its own
schematic hierarchy. The 12-part dedicated Ethernet 3.3V converter is electrically
integrated and routed. The remaining 49 Ethernet footprints are placement drafts:
the W5500, magnetics, clock, protection and SPI interface are not yet wired.
Root Rev1.2a PCB, schematics and manufacturing exports remain unchanged.

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
- 61 new footprint positions cover controller, jack, clock, bypass/bulk caps,
  reference termination network, straps, reset/interface and ESD package reserves.
- Existing 5 V converter, inductor, 3.3 V regulator, ADC divider and their support
  parts retain their original positions. The five rail/ground test pads form one
  row to the right of the RJ45. CS1 and CS2 sit to the left of the ESP32, at
  (82.5,51) and (88,51) mm, rotated 90 degrees, with front/back legends above.
  Three existing pull-ups move below/right of the PHY. These are the only ten
  existing footprint moves relative to Rev 1.2a.
- The stepper/watchdog IC positions, motor sockets and board outline are retained.
- The dedicated Ethernet supply is schematic-integrated and locally routed:
  U802 LMR36506R3RPER, 65V/600mA class, fed from protected +BATT, with a
  300mA Ethernet allocation. L801 is a 15uH shielded 4x4x3mm inductor. Input
  bulk/HF, bootstrap, VCC and output capacitors and EN resistors are placed
  above the original supply; the study envelope is x132.6..158.5/y53.3..59.35.
  Existing main5V/external1A allocation is not consumed by this addition.
- TP_ETH_3V3 moved to (157,56.25) for probe access beside the power island;
  it connects to the OUTPUT bus, despite nearby VIN capacitors.
- PROPOSED (not yet wired): U804 TXU0304PWR provides SPI power-domain
  isolation; Q802 gates its OE
  with Ethernet CS so it releases the shared MISO line when deselected.
  U803 is now TPS3808G33DBVR; Q801 supplies an open-drain manual-reset request.
  Their bypass and support parts are placed. Ethernet requires VBAT; USB-only
  logic operation must not back-power it. Firmware CS setup/hold is required.
- The new Ethernet bypass, crystal and strap positions were adjusted to keep
  MDI exits and a SPI via escape beside the crystal available. No additional
  existing Rev1.2a component was moved for this supply update.
- Detailed routing order, exact proposed power/interface pin nets, firmware
  requirements and remaining release checks are recorded in
  layout-review/power-routing-plan.txt and power-interface-design.json.
- No PoE circuitry or PoE connector claim is included. HR911105A is non-PoE and
  rated 0..70 C; broader temperature/PoE variants need a new connector selection.

CHECKS AND LIMITS
- Geometry review: no courtyard intersections involving the new/moved parts.
- USER UPDATE: the additional 15 mm antenna clearance was explicitly waived to
  simplify integration. J801 now enters that former clearance envelope;
  C801 also enters it slightly; see geometry.json for the exact screen.
  Nominal body-to-module lateral gap is 2.54 mm, with no footprint courtyard intersection. This is a geometric
  screen, not measured RF qualification. Wi-Fi range/throughput may suffer and
  must be measured with the real jack, plugged cable and enclosure.
- Obsolete signal branches and isolated copper were removed conservatively.
  Copper conflicting with new/moved pads was clipped; surviving ends were retained
  and displaced existing connections rerouted. See routing-progress.json and the
  work/ethernet-routing-20261024 audit files. Placement-era preservation reports
  describe the earlier checkpoint and are superseded for present copper geometry.
- Every new footprint remains excluded from BOM and CPL. Twelve power footprints
  have schematic-assigned nets; the other 49 retain net0 pending integration.
- The actual stack is FOUR layers: F.Cu, In1.Cu GND, In2.Cu split power, B.Cu.
  New routes avoid In1.Cu. Short In2 underpasses must be reviewed for power-plane
  continuity. Earlier two-layer routing notes were incorrect.
- Search reservations protect the jack isolation, clock and buck areas while
  restoring old nets. Final native jack isolation/copper voids remain pending;
  existing filled copper under the proposed jack is not yet qualified.
- D801 remains a provisional ESD package allocation, not a frozen MPN.
  Crystal CL/load caps, protection ratings, jack pinout/center-tap network and
  input-capacitor DC bias still require electrical review. Some package choices can
  change after that review, so this is not a promise that routing will be complete.
- W5500 pin 18 VBG is intentionally left floating in the circuit proposal;
  C809 is 4.7 uF for TOCAP pin 20, C810 is 10 nF for 1V2O pin 22.
- The current power-integrated schematic passes ERC with zero violations.
  PCB DRC is a progress check only: remaining draft net0 pads do not prove routed
  Ethernet connectivity. Existing silkscreen/library/dangling issues remain.

NEXT ELECTRICAL CHECKPOINT
1. Freeze crystal, ESD and exact magjack pin/center-tap/shield circuitry.
2. Integrate W5500 and SPI isolation/reset into the schematic. GPIO3/status LED
   changes and removal of U601 pads18/19 ground ties remain pending.
3. Route local bypass, clock, MDI pairs and then SPI; establish native isolation
   keepouts and verify actual layer stack, return paths and power-plane continuity.
4. Run complete schematic/PCB parity, ERC, DRC, BOM/CPL review and prototype tests.
   Do not use this in-progress variant for manufacturing.

Historical placement images/reports and proposal pin contracts remain useful
references. Current routing images and results are in layout-review/routing-*.
Do not rerun historical placement generators: they overwrite routing progress.

Fresh checkpoint QA: ../../validation/ethernet-checkpoint-20261024/README.txt
