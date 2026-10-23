Rev 1.2a placement correction — 23 October 2026

Cause: the first audit matched raw supplier pad numbers and centers. That is insufficient for mechanical wire-entry direction and is wrong for LEDs whose supplier symbol assigns A/K opposite to the KiCad symbol. These checks have now been separated.

Corrected exports only; PCB, schematics, BOM identities, placement centers and Gerbers are unchanged.
J102, J301, J401: 90 -> 270 degrees, wire openings to RIGHT board edge. C8465 supplier zero-angle wire entry is toward negative Y. Contact numbers are reversed deliberately; the two independent unpolarized terminal contacts have no intrinsic electrical polarity. PCB terminal labels continue to define the actual signals.
LED201, LED202, LED_FLT1, LED_FLT2: 180 -> 0 degrees. C2286/C2287 supplier pin 1 is A, pin 2 K; native KiCad LED pad 1 K, pad 2 A. Explicit functional mapping corrects polarity. Green C12624 and blue C2288 use pin 1 K and remain unchanged.
CAN J205 and RS485 J207 face LEFT; relay terminal outputs J505/J506 face DOWN. Their C72334 supplier-zero wire entry is positive Y; they require no change.

All 328 catalogue placements were reviewed again. Review categories and evidence are in component-orientation-review.csv. Every LED K/A mapping is asserted against the actual schematic XML netlist. All seven screw-terminal wire-entry vectors are asserted. All 328 origins and all SKUs are unchanged. The other 321 rotations are unchanged. Refer to review.json for exact changes and semantic mapping.

K501/K502 still require assembler alignment against the Omron drawing because the supplier hole pattern is inconsistent by about 0.55 mm. This review does not falsely certify those origins. J208 and jumper caps remain separately supplied/manual items. Existing catalogue footprint vs assembly-model differences cannot be universally certified without the actual JLC final order preview; user screenshot is the direct evidence for the C8465 body orientation correction.

The corrected CPL already includes all seven corrections. Upload the corrected file as a replacement; do not add a further 180 degrees to the corrected rows.
