# ABX-Motion Rev 1.2a checkpoint

Saved 23 October 2026 on rev-1.2-3axis-stepper.

This checkpoint incorporates the three-axis development since the earlier digital-I/O/OLED layout commit, including accepted user placement and routing refinements. It is not only a silkscreen revision.

- Three onboard DRV8462DDWR axes replace the two StepStick sockets; original JST motor connector style and external control interfaces are retained for three axes.
- Digital I/O now has eight JST sockets: five MIN/GND/MAX limit pairs (M1, M2, X, Y, Z), DIN1/GND/DIN2 and two auxiliary outputs. Added Z/DIN input filters and expander allocations are documented separately.
- Front/back axis legends and connector markings updated; local driver and watchdog package models included for portable rendering.
- Ground receiving copper, mask openings, thermal stitching and TIM legends added for heat management. Fabrication requires selected thermal holes to be filled/capped as documented; do not fill insertion holes.
- PCB and schematic title blocks and physical revision legends identify Rev 1.2a. Existing 0.15 mm project minimum clearance/track-width settings are restored rather than weakened for checks. Front copper gear badge and AUTOBOTIX / ABX-Motion Rev 1.2a silkscreen occupy the clear area near Q1; the rear badge moves 3 mm left and 1.5 mm up in back view. Electrical placement and routing are unchanged by these branding edits.

## Current limits and pending work

This is a CAD development checkpoint. No powered motor, fault or installed thermal qualification has been performed. Current limits depend on the completed cooling assembly and measured temperatures; package current limits are not board ratings. A matched Rev 1.2a JLCPCB prototype fabrication/assembly review package is provided under production/rev-1.2a-20261023/. It includes 74 catalogue SKUs / 328 placements, a separate low-profile J208 socket/mechanical BOM and the documented relay alignment review. No manufacturing order has been placed.

The earlier common machined HS1 plate is a superseded mechanical study. Custom machining is unavailable. The current direction is stock underside finned heatsinks, supplemented by narrow individual top-side sinks on the three DDW package bodies. Select exact parts, insulated interfaces and retention and verify solder-tail/lead/passive clearances before assembly. Archived thermal predictions apply to their stated study geometry, not automatically to the stock replacement.

Ethernet is a future revision option: W5500-class SPI Ethernet with a PoE-capable connector and optional isolated PoE daughterboard. Before implementation check GPIO allocation, supply headroom, antenna clearance, connector fit and external-DC priority/reverse-current protection. No Ethernet/PoE hardware is present in this checkpoint.

Root KiCad sources and local libraries are authoritative. Earlier design proposals/execution packets describe historical plans; they do not override the saved circuitry. Temporary routing candidates, backups and GUI session preferences are excluded from this commit.

## Placement correction, 23 October 2026

The JLCPCB CPL corrects J102/J301/J401 from 90 to 270 degrees so the two-pin terminal wire openings face the right edge. LED201/LED202/LED_FLT1/LED_FLT2 change from 180 to 0 degrees because supplier C2286/C2287 symbols number anode/cathode opposite to the native KiCad LED. Seven rotations change; every center and BOM identity is retained. Physical pin function and directional body constraints are now checked separately from raw pad numbers. All 328 placements were reviewed; all ten LED K/A mappings and all seven terminal wire-entry directions are asserted. The two relay alignment exceptions remain explicit. See validation/rev-1.2a-placement-fix-20261023/ and the corrected CPL in the prototype package. PCB circuitry, placement and Gerbers are unchanged.
