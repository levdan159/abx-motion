# Rev 1.2a thermal implementation and heatsink study

> Rev 1.2a checkpoint: PCB thermal copper/vias and TIM windows are implemented. The machined HS1 assembly below and its PDF/DXF/BOM are retained as a SUPERSEDED STUDY, not the current assembly instruction. Custom machining is unavailable. The current direction is stock underside finned heatsinks supplemented by individual top-side driver heatsinks; exact parts, retention, electrical clearance and installed performance remain to be selected and validated. Numerical results below describe the studied assembly, not the replacement stock-sink arrangement.

Dated 23 October 2026. Implemented in the root PCB after CAD verification. Electrical circuitry, component positions, all original tracks/vias and the four-layer 1 oz stackup are retained. This is an analytical design review and a mechanical machining specification, not powered thermal qualification. The later Rev 1.2a prototype export is in production/rev-1.2a-20261023/; it does not qualify a cooling assembly.

## Implemented PCB changes

- U701/X: 18 new central ground vias; U702/Y: 16; U703/Z: 18. All new barrels are 0.30 mm nominal drill / 0.60 mm diameter. Actual safe positions avoid existing phase/signal tracks on every copper layer. The original edge arrays remain. Including pre-existing barrels, the three exposed contact areas contain 31, 28, 30 ground vias respectively.
- Three solid B.Cu GND receiving zones, 8 x 17 mm. Their 7.6 x 16.6 mm solder-mask openings expose connected GND only. Back silkscreen outlines and X/Y/Z TIM markings identify them. No paste is added on the back. The TI 3.8 x 8 mm front exposed-pad window and segmented stencil stay unchanged.
- Q1: three additional **V_FUSED drain-net** heat-spreading vias adjacent to the drain copper. These are deliberately not ground vias. The existing drain copper is retained on both faces; no live-net copper is newly exposed.
- U2: bounded ground copper extension and one safe additional plane stitch at the ground lead. U3/ESP32: two safe ground stitches below the module; existing twelve plated EP ground holes and the module-body ground spreader remain. Unsafe candidates were omitted instead of moving signals.
- U1 buck already has eight EP thermal holes. DC bridge FETs already have power-net stitching and backside islands; DRV8701 packages have ground EP construction. These features were checked and retained rather than adding indiscriminate vias or enlarging switching nodes.
- PCB drawings show HS1, existing M3 mounting references, RF notch and insulating-TIM placement. No new PCB holes, component relocations, electrical changes or routing replacements.

## Fabrication requirement: essential, not optional

The central driver vias intersect the soldered thermal pad. Specify **IPC-4761 Type VII resin-filled, planarized, copper-capped on both faces**, with the final board finish over the cap. Tenting alone is not a substitute. Use `filled-capped-vias.csv`: 89 selected driver GND vias, including original edge barrels exposed by the bottom contact windows. The coordinates are global PCB XY, mm. Do not fill connector/mounting/lead-insertion PTH holes. The12 specifically listed U3 pad41 EP thermal holes ARE intentionally selected for fill/cap; they are not insertion holes. A fab may choose to fill all ordinary vias; it must still distinguish real component holes. Request minimum 25 um finished barrel copper for the modeled controlled case; confirm how nominal hole size and plating are quoted. Epoxy is NOT assumed to conduct like copper in the calculation.

Retain four layers, 35 um copper per layer, 1.6 mm finished thickness. Do not silently select 2 oz: fine-pitch clearances need separate fabrication review. Request assembly X-ray of all three driver EP joints, target void area <=20% with no large central void; actual process acceptance should be agreed with assembler. This target is a process requirement, not achieved evidence. ENIG is suitable for the large back contact windows. Mask openings and a visual copper patch cannot substitute for filled/capped processing.

## Low-profile screw-mounted common heatsink

Chosen stock: **Fischer SK 44 150 SA**, 159 mm wide, 15 mm overall height, nominal 4 mm base. Cut a 105 mm length. Custom finished assembly identifier **ABX-HS1-002**. This is machined stock, not an off-the-shelf drop-in SKU. For small quantities ask the supplier to cut/machine the SK 44 profile or buy the 150 mm stock and trim it to 105 mm. The 100 mm catalogue part is a thermal/section reference; it is too short for robust edge distances at all four retained mounting holes.

Mount the 159 x 105 mm piece under the existing 157 x 105 mm PCB, global bounds X44..203/Y48..153. It overhangs 1 mm at each long side. Fins run along PCB Y. Remove the entire RF notch X76.5..125.5/Y48..68.5 (49 x 20.5 mm); no fastener, boss, metal burr or enclosure bridge may refill this space. This provides >=15 mm clearance around the native antenna rectangle X91.5..110.5/Y46..53.5 on the in-board sides. The board's existing RF copper/layout is unchanged. Verify installed radio throughput/range.

Machine 1.60 +/-0.03 mm from the stock flat face **except the three 8 x 17 mm stepper bosses AND the U2 3.6 x 3.0 mm boss** listed below. The remaining mainland base is nominally 2.40 mm thick, with the original approximately 11 mm fins. Contact bosses remain at the original stock face. Machine/verify the base to the actual purchased profile, not to a synthetic fin pitch. The four screw seats are on the recessed mainland face, not raised islands. Deburr all edges; internal notch corner radius <=1 mm is acceptable if no metal intrudes into the specified antenna clearance. Contact face flatness <=0.05 mm locally; assembled relative boss coplanarity <=0.05 mm; target surface Ra<=1.6 um. No bare metal should touch the PCB anywhere except an intentional mounting-ground connection if chosen in the enclosure assembly.

Bosses (global XY, mm), chosen centre Y123.75, aligned to the board contact windows:

| Axis | X range | Y range | Boss / TIM size |
|---|---|---|---|
| X | 84..92 | 115.25..132.25 | 8 x 17 mm |
| Y | 104..112 | 115.25..132.25 | 8 x 17 mm |
| Z | 124..132 | 115.25..132.25 | 8 x 17 mm |

Holes: 3.4 mm clearance at (49.5,52.5), (197.5,52.5), (49.5,148.5), (197.5,148.5). Use four 2.00 +/-0.03 mm insulating hard spacers between the PCB underside and recessed mainland; M3x10 screws through front nylon washers, existing PCB holes, spacers and sink, retained by M3 nuts. Mill an 8 mm diameter tool/nut clearance in the fin side around each hole without thinning the 2.4 mm base. Confirm bolt stack with actual washers/nuts; nominal total washer+PCB+spacer+base+nut=8.9 mm, leaving about1.1 mm protrusion. No new PCB holes are required. Existing H1-H4 are ground plated; metal screws can bond the sink to GND. Choose and document this bond deliberately; anodizing is not dependable electrical isolation or a dependable bond.

TIM: **Bergquist GP5000S35-0.020-02-0404 / GAP PAD TGP 5000**, 0.508 mm sheet, 5 W/(m K), fiberglass reinforced, electrically insulating. Cut three 8 x 17 mm driver pads plus one3.6 x3.0 mm U2 pad. Nominal assembled thickness 0.40 mm (21% compression); never replace with graphite, conductive tape or grease alone. A single pad's sheet thickness must not be used as a calibrated spacer. Validate the force/compression curve with the TIM supplier and assembled flatness; body hardness is not a clamp-force specification. Fit to hard stops progressively, inspect for board bow; if loaded bow near the drivers exceeds0.10 mm or the contact imprint is incomplete, stop and shim/rework the cooler/spacer stack rather than overtighten it. A pressure/flatness validation is still needed before this mechanical assembly is released.

Height: main metal face 2.00 mm below PCB, boss face0.40 mm below PCB. Remaining base2.40 mm plus fins~11 mm gives **15.4 mm nominal added height below PCB**, excluding screw tips already within the fin clearance. Allow tolerance and verify purchased profile. The PCB solder tails must be trimmed to **0.8..1.0 mm below the PCB** without cutting into solder fillets; this leaves >=1 mm mainland clearance. Check every protruding header, relay, fuse and connector lead; do not pull the sink against long tails. No backside electronic components are currently populated (only a logo footprint). Use the largest compatible insulating hard spacers and measure final bow/contact. Do not clamp on the driver bodies from above.

Cooling condition: no fan. Use natural convection with channels open at both ends; prefer vertical fins/vertical board. Provide at least10 mm external air space beyond fin tips and an unobstructed inlet/outlet. The low metal profile does not remove the need for ventilation. A closed enclosure or horizontal fins pointing down requires an installed thermal rerating. The selected HS1 machining retains FOUR bosses: the three stepper drivers and U2. Q1/U1 contact rectangles on B.Fab remain future options only. The separate ESP pad is inside the main cooler RF notch and is NOT an HS1 boss. Adding a live-net contact requires insulating TIM and a separate thermal/tolerance review. They are not silently counted as established cooling.

## Thermal calculation and useful limits

Reproducible script and native filled copper extraction are under `work/thermal-20261023/`. The finite-difference network includes all four actual copper layers, FR4, explicit plated barrels, solder, package junction-to-bottom0.7 C/W, TIM and a local base/contact allowance. It does not replace the PCB by TI's JEDEC thetaJA or treat the0.7 C/W package value as junction-to-heatsink. Boundary is a cropped9 x17.5 mm local patch with adiabatic sides: omitted lateral spreading and top/lead heat paths can lower real resistance. Whole-board hot spots, exact die gradients, contact stress and enclosure airflow are not solved. Mesh0.5 mm, with0.25 mm Y-axis sensitivity; 15% local resistance reserve and10 C unexplained-temperature allowance are engineering allowances, not validated error bounds. Nominal TIM contact8x17 is used; the narrow0.2 mm mask rim is neglected in the solver and covered only by sensitivity/reserve, not a guaranteed bound.

Controlled construction: 25 um barrel copper,35 um layers, solder75 um with80% coverage,0.40 mm TIM at5 W/(m K), local base/contact1.0 C/W. Interface sensitivity:18 um barrel, lower laminate/copper/solder conductivities,150 um solder50% coverage,0.508 mm TIM at3 W/(m K),1.5 C/W base/contact. Actual fab/TIM values are not measured.

| Local path, incl package/TIM/base | Original | Improved |
|---|---:|---:|
| Controlled, across axes/meshes | 15.6..17.0 C/W | 8.0..9.0 C/W |
| Adverse interface sensitivity | 23.2..25.0 C/W | 12.2..13.5 C/W |

Per-driver loss model: P=2 I_RMS^2 (R_H+R_L) +2 VM I_RMS t_RF f_PWM +VM I_VM +P_VCC. Hot125 C max H+L=0.184 ohm; hot typical0.143. Current+5% is a sensitivity, not a guaranteed bound at every microstep or with arbitrary ripple. Example29.4 V,30 kHz,140 ns,11 mA supply plus33 mW VCC allocation. Actual3.3 V VCC and switching times are not a guaranteed table corner. The32 V /50 kHz /210 ns case is an engineering stress assumption, not a promised vendor worst-case bound.

The manufacturer catalogue shows the SK 44 is 159 x 15 mm with a 4 mm base (about11 mm fins). Distributor listings for an unmodified100 mm length vary around1.6..2.0 C/W; these are catalogue conditions, not the machined installed assembly. Neither applies automatically after milling, RF cutout, distributed contact and enclosure installation. Use **<=2.5 C/W installed shared sink-to-ambient as a design requirement**, sweep2/2.5/3.5/5 C/W, and measure the actual assembly. There is **no manufacturer-qualified thermal resistance for ABX-HS1-002 yet**.

At40 C ambient, all3axes, hot maximum resistance, +5% current, local path worst-axis x1.15, additional5 W captured board heat, sink2.5 C/W and10 C allowance:

| Command / phase RMS | Each driver loss | Screening Tj | Interpretation |
|---|---:|---:|---|
| 2 A | 2.50 W | 107.0 C | conditional prototype target; validate |
| 2.5 A | 3.54 W | 125.6 C | fails125 C target; no continuous all-axis approval |
| 3 A | 4.79 W | 147.7 C | fails125 C target; no continuous all-axis approval |
| 3.5 A | 6.23 W | 173.5 C | fails125 C target; no continuous all-axis approval |

Values above125 C are failed screening calculations using fixed125 C resistance, **not reliable physical equilibrium predictions**. At2 A the50 kHz switching stress gives about123 C at the specified2.5 C/W target, but worsens to about162 C at5 C/W; the30 kHz hot-max case is about138 C at5 C/W. These are screening sensitivities and require measured switching and installed convection. Therefore2 A is a conditional design target, not a universal product rating. At3.5 A command+5% current exceeds the DDW nominal3.5 A RMS/5 A fullscale limit; never program that combination. JST-XH is specified3 A withAWG22; driver thermal capacity does not upgrade the connector or cable. Higher-current operation requires measured current/ripple, connector rise, duty, switching ceiling and thermal performance; prefer separate higher-power revision for continuous all-axis3.5 A.

Additional5 W is a shared-heating sensitivity, not a complete worst-case board power budget. External5 V power dissipated off-board is not sink heat; if inside an enclosure it warms the air and must be accounted for. DC bridge load/copper and Q1 heat beyond this allowance further reduce the available current. Do not treat150 W electrical output as150 W PCB heat, or assume DC channels are off unless tested that way.

## Other heat sources and remaining concerns

| Source | Assessment and action |
|---|---|
| Q1 input P-FET | Main shared-current concern. Hot sensitivity R=0.018x1.65=0.0297 ohm gives0.74/2.97/6.68 W at5/10/15 A battery current. The1.65 hot factor comes from a typical curve/ratio, not a guaranteed hot maximum. 20/25 A gives11.9/18.6 W and cannot be claimed continuous with the present copper. Three added drain stitches help spread heat but do not establish a30 A board rating. The battery's30 A capability is not a permitted PCB load. Both DC motors150 W for1 s plus steppers need actual input current/SOA and transient cooling tests; steady-state thetaJA cannot approve1 s bursts. |
| U1 + L1 buck |8 existing ground EP holes retained.10 W delivered at85..90% assumed efficiency implies1.11..1.76 W total converter/inductor loss; efficiency is a sensitivity, not this board's measurement. Keep SW copper compact. Check inductor saturation, DCR, temperature rating and load duty against the actual fitted part; an unspecified15 uH part is not a thermally qualified SKU. |
| U2 AP2112 SOT25 | **Remaining thermal/current bottleneck.** 5V->3.3V dissipates1.7xI:0.51 W at300 mA,0.85 W at500 mA,1.02 W at600 mA. Datasheet thetaJA184 C/W is a reference, not this board's actual value; applying it as a warning screen gives134/196/228 C at40 C ambient before allowances. To keep125 C with10 C allowance at500 mA requires effective<=88 C/W. Added copper/stitching helps but does not prove that. A larger ground island cannot turn the 600 mA LDO into a higher-current supply. Measure3V3 total/current duty and U2 temperature; if sustained loading needs that envelope, a regulator change is required as a separate small electrical task. No supply redesign was made here. |
| U3 ESP32-S3 module | Existing12 plated EP holes, ground spreader and two additional lower stitches support board spreading. Budget up to1.65 W as a power sensitivity (3.3Vx0.5A), with real average radio/CPU duty measured. The main HS1 cooler still preserves its antenna notch. A direct ESP ground contact is now provided, with the RF restriction below. The common sink has an RF notch; direct sink cooling of the module is not claimed. Keep shield/body airflow free; module ambient limit follows N8R2's manufacturer variant specification. |
| DC MOSFETs / DRV8701 | Existing high-side supply vias and low-side phase-net backside islands retained. Estimate hot conducting-pair loss I_RMS^2x(2xR_FET), plus switching, gate and shunt losses using the real PWM. For an illustrative0.004 ohm hot FET and6.25 A path this is0.31 W per bridge conducting pair, excluding switching. That assumed resistance must be replaced by the actual gate-drive/hot device bound; stalling current is not150W/24V. Drain copper is electrically live: do not bridge FET islands with a bare common sink. |
| Shunts / fuse / relays / terminals | 5 mohm shunt loses0.20 W at6.25 A,0.50 W at10 A,2.0 W at20 A (actual shunt rating and pulse curve govern). Fuse/contact/relay resistances causeI^2R heat; keep solder joints accessible and measure rise. Capacitor lifetime depends on case/ripple temperature; keep electrolytics away from hot exhaust and below their fitted-part ratings. |
| D2 TVS | A transient protector, not a continuous brake resistor. Thermal vias/copper cannot make recurring motor regeneration safe without an energy/duty envelope. No dissipated-energy rating is invented here. |

## CAD verification and first-hardware acceptance

Verification evidence is `work/thermal-20261023/verification.json`. Required: zero errors, zero opens, zero schematic parity; all original footprint/pad geometry and copper UUID/net/geometry unchanged; exact original connected-pad partitions retained; all exposed contact samples are GND. Existing warnings are enumerated separately and not waived as passing thermal evidence.

Before powering: inspect filled/capped process confirmation, EP solder X-ray and correct TIM/contact imprint; inspect each trimmed lead against the cooler, confirm no short from sink to+BATT/phase nets, verify all hard stops and bow. Bench testing uses the intended24 V battery class through suitable fuse/current control; no unsupported12 V bring-up requirement is imposed. Instrument each driver case, back pad/sink, Q1, U1/L1, U2, ESP shield, shunts and motor connectors; do not equate the top-surface measurement with junction temperature using thetaJC. Run1axis then3axes at1/1.5/2 A, hold and move with representative motors/radio/IO, logging PWM/current/ripple until temperature stabilizes; repeat at40 C local ambient and installed orientation/enclosure. Abort on thermal warning, supply sag or abnormal rise, with an initial conservative driver-case threshold80 C until case-to-junction correlation is established.80 C is a test stop setting, not a qualified operating rating. Test higher current only after the lower-current envelope is known. TargetTJ<=125 C with allowance and connector rise<=20 C. Use motor stall/short/hot-plug only within a separately defined protection test; this thermal review does not authorize destructive fault energy.

## Update B: relocated legend and two new exposed contacts

The underside legend frame was translated exactly30 mm LEFT in the underside view: from X94..146/Y58..94.2 to X124..176/Y58..94.2 in PCB coordinates (the underside view mirrors X). Its0.75 mm body text now states7S/29.4 V full-charge,32 V design maximum, actual2 A buck/600 mA LDO component classes with shared/thermal limits, three-axis SPI setup, M1/M2/X/Y/Z limits, the two J608 digital inputs, current connector designators and hardware inhibit. The previous100 W motor target and stale8-limit/planned-interface wording were removed; electrical power/current claims require their documented operating envelope.

New ESP contact: B.Cu ground receiving copper X97.3..101.7/Y60.26..64.66, with a **4.0 x4.0 mm exposed mask window** at X97.5..101.5/Y60.46..64.46. It sits beneath the module ground EP and its12 plated ground holes. A4.4 x4.4 mm insulating TIM piece can cover the copper receiving area; the square collector and opening are centred on the existing thermal-hole array at(99.5,62.46), with existing signal copper fully masked. No trace or component was moved. This is an optional separate-cooler provision: **placing metal against this direct EP contact does not meet the previously reserved15 mm antenna housing clearance**, even though it is beneath the shielded module body rather than the antenna artwork. HS1 still has the full RF notch and no ESP boss. Do not silently bridge that notch. Before selecting/fitting a separate metal ESP sink, qualify radio throughput/range with it installed; its maximum envelope must stay clear of the actual antenna area and other pads. No RF performance or ESP junction-temperature rating is established by opening this ground pad. If15 mm metal clearance is mandatory for an enclosure, leave this pad without a metal sink and use board spreading or a separately engineered dielectric thermal path instead.

New U2 contact: ground copper X133.3..136.9/Y78.6..81.6 (3.6 x3.0 mm); exposed window X133.5..136.7/Y78.8..81.4 (3.2 x2.6 mm). This is below/adjacent to the regulator GND lead and its existing ground stitches. Retain a matching **3.6 x3.0 mm,1.60 mm-high U2 boss** on HS1; use the same0.508 mm TGP5000 sheet, target0.40 mm assembled. The additional small contact increases local pressure sensitivity: seat to hard stops, check the full4-boss imprint and board bow; do not use bolt torque to force contact. No600 mA continuous board rating is implied.

Updated fill/cap list: **104 selected thermal barrels/holes**: the previous89 stepper vias plus the ground vias and12 module-EP thermal holes exposed by these new windows. Do not give the fabricator a blanket instruction to plug actual connector or mounting holes. The two new ground zones and mask windows were checked against the actual filled B.Cu; existing copper/placement is retained.

Heatsink revision ABX-HS1-002 now uses **SK44 150 SA**, cut from150 to105 mm length, with a159 x15 mm section and4 mm nominal original base. The roughly11 mm fins are taller than the previous6 mm fins. Overall nominal projection beneath the PCB is **15.4 mm**, below the user's20 mm allowance; ventilation clearance is additional. Catalogue thermal resistance is not inherited after cutting/pocketing/notching. The new installed target is<=2.5 C/W, with a conservative5 W non-stepper heat allowance; qualify the assembly before claiming this target.

## Sources checked23Oct2026

- TI DRV8462 RevB, sections6.4/6.5,8.2.4,9/11 andDDW0044E drawing: https://www.ti.com/lit/ds/symlink/drv8462.pdf
- TI PowerPAD construction: https://www.ti.com/lit/an/slma002h/slma002h.pdf
- Fischer SK44 section/curve (manufacturer catalogue hosted by distributor): https://static6.arrow.com/aropdfconversion/715cb6bc58f0fbb9cad13b599d92bd1295de44b6/heatsinks.pdf
- StockSKU: https://www.digikey.com/en/products/detail/fischer-elektronik/SK-44-150-SA/25832008
- Henkel insulatingTIM datasheet: https://datasheets.tdx.henkel.com/BERGQUIST-GAP-PAD-TGP-5000-en_GL.pdf
- AP2112: https://www.diodes.com/datasheet/download/AP2112.pdf
- Q1: https://www.vishay.com/docs/66963/sqj459ep.pdf
- DC FET: https://www.ti.com/lit/ds/symlink/csd18540q5b.pdf
- Buck: https://www.ti.com/lit/ds/symlink/lmr36520.pdf
- ESP32 module: https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf
- ESP32 ground and antenna guidance: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html
- JST-XH: https://www.jst-mfg.com/product/pdf/eng/eXH.pdf
- JLC via-in-pad process: https://jlcpcb.com/help/article/via-in-pad-pofv-guide
- PCBWay via covering: https://www.pcbway.com/pcb_prototype/PCB_Via_Covering.html

Stock was checked online; no parts were ordered or reserved. Raw downloaded PDFs and hashes are retained in the work folder. No powered tests, fabricated cooler fit, contact-pressure measurement or supplier process approval has been completed.
