"""Derive placement origins/rotations from supplier numbered pad centers; never saves PCB."""
from pathlib import Path
import json,csv,math,re,xml.etree.ElementTree as E,collections
import pcbnew as p
import numpy as np
O=Path(__file__).resolve().parent;ROOT=O.parents[1];SUP=O/'supplier';sel=json.loads((O/'selections.json').read_text());b=p.LoadBoard(str(ROOT/'abx-motion.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()}
cache={}
for c in set(sel.values()):
 root=E.parse(SUP/f'{c}-1.svg').getroot();g=next(g for g in root if 'c_para' in g.attrib);ox,oy=map(float,g.attrib['c_origin'].split(','));pp=collections.defaultdict(list)
 for e in g.iter():
  if e.attrib.get('c_partid')=='part_pad':
   x,y=map(float,e.attrib['c_origin'].split(','));pp[e.attrib['number']].append([(x-ox)*.254,(y-oy)*.254])
 cache[c]=dict(pp)
rules=json.loads((O/"orientation-rules.json").read_text())
results=[]
for ref,c in sorted(sel.items()):
 f=fs[ref];pads=[q for q in f.Pads() if q.GetNumber() and q.IsOnLayer(p.F_Cu)];unknown=[];pairs=[]
 for n,points in cache[c].items():
  names=[rules["pin_mapping"].get(c,{}).get(n,n)]
  if c=='C86513' and n in ['5','6','7','8']:names=['5']
  if ref=='J201':names={'A1B12':['A1','B12'],'B1A12':['B1','A12'],'B4A9':['B4','A9'],'A4B9':['A4','B9']}.get(n,[n]) if n not in ['1','2','3','4'] else ['S1']
  targets=[q for q in pads if q.GetNumber() in names]
  if ref=='F1':targets=pads
  if not targets:unknown.append(n);continue
  for xy in points:pairs.append((n,xy,targets))
 if not pairs:results.append({'ref':ref,'code':c,'status':'NO MATCHING PADS','unknown':unknown});continue
 best=None
 for a in [0,90,180,270]:
  rad=math.radians(-a);R=np.array([[math.cos(rad),-math.sin(rad)],[math.sin(rad),math.cos(rad)]])
  # First use unambiguous matching pad centers; split pads use their center average.
  ts=[np.mean([[p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y)] for q in targets],axis=0)-R@xy for _,xy,targets in pairs]
  shift=np.median(ts,axis=0)
  for _ in range(3):
   ts=[min([np.array([p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y)]) for q in targets],key=lambda v:np.linalg.norm(v-(shift+R@xy)))-R@xy for _,xy,targets in pairs]
   shift=np.median(ts,axis=0)
  ds=[min(math.hypot(*(shift+R@xy-np.array([p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y)]))) for q in targets) for _,xy,targets in pairs]
  score=float(np.mean(np.square(ds)))
  if best is None or score<best[0]-1e-9:best=(score,a,shift,ds,R)
 score,a,shift,ds,R=best;outside=[]
 if ref in rules.get('fixed_origins',{}):
  shift=np.array(rules['fixed_origins'][ref]);ds=[min(math.hypot(*(shift+R@xy-np.array([p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y)]))) for q in targets) for _,xy,targets in pairs]

 if ref in rules['expected_wire_entry']:
  actual=R@np.array(rules['wire_entry_at_supplier_zero'][c]);expected=np.array(rules['expected_wire_entry'][ref]);assert np.linalg.norm(actual-expected)<1e-6,(ref,a,actual,expected)

 for n,xy,targets in pairs:
  xx,yy=shift+R@xy;shape=p.SHAPE_CIRCLE(p.VECTOR2I(p.FromMM(float(xx)),p.FromMM(float(yy))),p.FromMM(.003))
  if not any(p.SHAPE.Collide(q.GetEffectiveShape(p.F_Cu),shape,0) for q in targets):outside.append(n)
 status='PASS' if not outside and not unknown else 'REVIEW'
 if ref in ['K501','K502']:status='RELAY MANUFACTURER ALIGNMENT REQUIRED'
 results.append(dict(ref=ref,code=c,value=f.GetValue(),footprint=str(f.GetFPID().GetLibItemName()),x=round(float(shift[0]),6),y=round(float(shift[1]),6),rotation=a,native_rotation=f.GetOrientationDegrees(),max_residual_mm=round(max(ds),6),outside=outside,unknown=unknown,status=status,orientation_basis=rules['basis'].get(c,'Supplier numbered pad geometry; native pin mapping retained.'),supplier_to_native_pad_mapping=json.dumps(rules['pin_mapping'].get(c,{}),sort_keys=True)))
(O/'placements.json').write_text(json.dumps(results,indent=2)+'\n')
with open(O/'placements.csv','w',newline='') as ff:
 w=csv.DictWriter(ff,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
print(collections.Counter(r['status'] for r in results))
for r in results:
 if r['status']!='PASS':print(r)
