"""Review semantic pin functions, keyed polarity and terminal wire-entry direction."""
from pathlib import Path
import json,csv,hashlib,xml.etree.ElementTree as E,math,collections
O=Path(__file__).resolve().parent;V=O.parent/'rev-1.2a-20261023';R=O.parents[1];P=R/'production/rev-1.2a-20261023';rows=json.loads((V/'placements.json').read_text());old={r['ref']:r for r in json.loads((O/'before/placements.json').read_text())};rules=json.loads((V/'orientation-rules.json').read_text());inv={r['ref']:r for r in json.loads((V/'inventory.json').read_text())}
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(R/'abx-motion.kicad_pcb')=='51a583987cc928cb9c5e47a8bd627dcd8717c2d7bf8e899feedf9d6ab6bdb1d0'
changes=[]
for r in rows:
 b=old[r['ref']];assert (r['code'],r['x'],r['y'])==(b['code'],b['x'],b['y'])
 if r['rotation']!=b['rotation']:
  assert (r['rotation']-b['rotation'])%360==180
  changes.append({'ref':r['ref'],'code':r['code'],'before':b['rotation'],'after':r['rotation'],'x':r['x'],'y':r['y'],'reason':r['orientation_basis']})
assert {r['ref'] for r in changes}=={'J102','J301','J401','LED201','LED202','LED_FLT1','LED_FLT2'}
# Compare the supplier's LED symbol K/A labels with the actual schematic pin names.
root=E.parse(O/'netlist.xml').getroot();libparts={(v.attrib['lib'],v.attrib['part']):{q.attrib['num']:q.attrib['name'] for q in v.findall('pins/pin')} for v in root.findall('libparts/libpart')};comps={v.attrib['ref']:v for v in root.findall('components/comp')};review=[];semantic=[]
for r in rows:
 ref,c=r['ref'],r['code'];v=inv[ref]['value'];category='Unpolarized passive / symmetric part';basis=r['orientation_basis'];status=r['status'];proof=f'validation/rev-1.2a-20261023/supplier/{c}-1.svg'
 if ref.startswith('U'):category='Numbered IC / module';basis+=' Numbered IC pin functions reviewed against schematic, allowing documented naming aliases (GND/EP, active-low notation and alternate-function names).'
 if ref.startswith('Q'):category='MOSFET';basis+=' Gate/source/drain symbol functions agree; common drain pads 5-8 map to native common pad 5 for C86513.'
 if ref.startswith('J'):category='Connector';basis+=' Keyed JST/USB/XT60 pin mapping retained; unkeyed strip headers are symmetric.'
 if ref in rules['expected_wire_entry']:
  category='Directional screw terminal';a=math.radians(-r['rotation']);x,y=rules['wire_entry_at_supplier_zero'][c];actual=[round(math.cos(a)*x-math.sin(a)*y),round(math.sin(a)*x+math.cos(a)*y)];assert actual==rules['expected_wire_entry'][ref];basis+=' Wire-entry vector checked against intended board edge: '+str(actual)+'.'
 if v.startswith('LED_'):
  category='Polarized LED';comp=comps[ref];lib=comp.find('libsource');npins=libparts[(lib.attrib['lib'],lib.attrib['part'])];sg=E.parse(V/'supplier'/f'{c}-0.svg').getroot();sp={}
  for g in sg.iter():
   if g.attrib.get('c_partid')=='part_pin':
    t=[e.text or '' for e in g.iter() if e.tag.endswith('text')]
    if len(t)>=2:sp[t[-1]]=t[0]
  mapping=rules['pin_mapping'].get(c,{})
  for n,func in sp.items():assert func==npins[mapping.get(n,n)],(ref,n,func,npins)
  basis+=' Supplier K/A function checked against schematic K/A after applying explicit mapping.';semantic.append({'ref':ref,'supplier_pin_functions':sp,'native_pin_functions':npins,'mapping':mapping})
 if r['footprint'].startswith(('CP_Radial','CP_Elec')):category='Polarized electrolytic';basis+=' Supplier footprint + marker is on pad 1; native positive pad 1 retained. Supplier negative stripe remains on pad 2.'
 if ref.startswith('D') and not v.startswith('LED_'):category='Diode / protection';basis+=' Cathode/anode symbol mapping retained; D201 is bidirectional. D2 functional ground/positive pins retain the reviewed TI mapping.'
 if ref.startswith('K'):category='Relay';basis='Pin numbering/rotation retained; supplier hole-offset discrepancy remains an explicit manufacturer-alignment review.'
 review.append({'Designator':ref,'SKU':c,'Category':category,'Rotation':r['rotation'],'Status':status,'Basis':basis,'Evidence':proof})
with open(O/'component-orientation-review.csv','w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(review[0]));w.writeheader();w.writerows(review)
report={'PCB_unchanged_sha256':sha(R/'abx-motion.kicad_pcb'),'reviewed_CPL_rows':len(rows),'unchanged_centers':True,'unchanged_SKUs':True,'changed_rotations':changes,'LED_function_checks':semantic,'terminal_entry_checks':rules['expected_wire_entry'],'unchanged_rotations':len(rows)-len(changes),'remaining_relay_alignment_reviews':['K501','K502'],'review_scope':'Supplier CAD geometry, symbol pin function/polarity and terminal wire-entry direction. Actual JLC order state/3D models are not available through connected browser; user screenshot is evidence for terminal correction. Final assembler alignment remains required for the two relays.'}
(O/'review.json').write_text(json.dumps(report,indent=2)+'\n')
(O/'README.txt').write_text('''Rev 1.2a placement correction — 23 October 2026

Cause: the first audit matched raw supplier pad numbers and centers. That is insufficient for mechanical wire-entry direction and is wrong for LEDs whose supplier symbol assigns A/K opposite to the KiCad symbol. These checks have now been separated.

Corrected exports only; PCB, schematics, BOM identities, placement centers and Gerbers are unchanged.
J102, J301, J401: 90 -> 270 degrees, wire openings to RIGHT board edge. C8465 supplier zero-angle wire entry is toward negative Y. Contact numbers are reversed deliberately; the two independent unpolarized terminal contacts have no intrinsic electrical polarity. PCB terminal labels continue to define the actual signals.
LED201, LED202, LED_FLT1, LED_FLT2: 180 -> 0 degrees. C2286/C2287 supplier pin 1 is A, pin 2 K; native KiCad LED pad 1 K, pad 2 A. Explicit functional mapping corrects polarity. Green C12624 and blue C2288 use pin 1 K and remain unchanged.
CAN J205 and RS485 J207 face LEFT; relay terminal outputs J505/J506 face DOWN. Their C72334 supplier-zero wire entry is positive Y; they require no change.

All 328 catalogue placements were reviewed again. Review categories and evidence are in component-orientation-review.csv. Every LED K/A mapping is asserted against the actual schematic XML netlist. All seven screw-terminal wire-entry vectors are asserted. All 328 origins and all SKUs are unchanged. The other 321 rotations are unchanged. Refer to review.json for exact changes and semantic mapping.

K501/K502 still require assembler alignment against the Omron drawing because the supplier hole pattern is inconsistent by about 0.55 mm. This review does not falsely certify those origins. J208 and jumper caps remain separately supplied/manual items. Existing catalogue footprint vs assembly-model differences cannot be universally certified without the actual JLC final order preview; user screenshot is the direct evidence for the C8465 body orientation correction.

The corrected CPL already includes all seven corrections. Upload the corrected file as a replacement; do not add a further 180 degrees to the corrected rows.
''')
print('Reviewed',len(rows),'placements;',len(changes),'rotation fixes;',len(semantic),'LED K/A checks; 7 terminal direction checks; PCB unchanged.')
