DRC cleanup2026-10-24: project copies of intentionally customized footprints.
These preserve the existing PCB pad/drill geometry and3D orientations.
The reviewed-library-map.json under work/drc-cleanup-20261024 records aliases.
Matching schematic footprint fields were updated together with the PCB.
TIM_GND_4x4_Bottom provides the ESP rear GND TIM copper/mask opening with no
paste aperture; it is board-only and excluded from assembly exports.
Shared Motor_Channel symbols use shared motor-terminal/DRV8701 footprint IDs.
Do not update these placed parts from stock libraries: custom pad sizes,
thermal structures and model transforms are intentional.
