"""Read-only placement audit. Never routes, saves PCB, or rewrites CPL."""
from pathlib import Path
import csv,json,math,hashlib,xml.etree.ElementTree as E,html,collections
import pcbnew as p
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[1]
board=ROOT/'abx-motion.kicad_pcb';before=hashlib.sha256(board.read_bytes()).hexdigest()
b=p.LoadBoard(str(board));fs={f.GetReference():f for f in b.GetFootprints()}
cpl=list(csv.DictReader(open(ROOT/'production/abx-motion-jlcpcb-cpl.csv')))
bom=list(csv.DictReader(open(ROOT/'production/abx-motion-jlcpcb-bom.csv')))
byref={ref:row for row in bom for ref in row['Designator'].split(',')}
assert len(byref)==sum(len(row['Designator'].split(',')) for row in bom)==len(cpl)==239
assert set(byref)=={r['Designator'] for r in cpl}
cache={}
for fn in sorted((OUT/'supplier').glob('*-1.svg')):
 root=E.parse(fn).getroot();g=next(g for g in root if 'c_para' in g.attrib)
 ox,oy=map(float,g.attrib['c_origin'].split(','));pp={}
 for el in g.iter():
  if el.attrib.get('c_partid')=='part_pad':
   x,y=map(float,el.attrib['c_origin'].split(','));pp.setdefault(el.attrib['number'],[]).append([(x-ox)*.254,(y-oy)*.254])
 cache[fn.stem.split('-')[0]]={'pads':pp,'source':str(fn),'origin':[ox,oy]}
assert len(cache)==66
(OUT/'supplier/combined-pad-cache.json').write_text(json.dumps(cache,indent=2)+'\n')
SVG='{http://www.w3.org/2000/svg}'
results=[];panels=[];seen=set()
for r in cpl:
 ref=r['Designator'];base=ref.split('_')[0] if ref.startswith(('U501_','U502_')) else ref;f=fs[base]
 code=byref[ref]['LCSC Part #'];v=cache[code]
 angle=float(r['Rotation']);a=math.radians(-angle);co,si=math.cos(a),math.sin(a)
 cx=float(r['Mid X'].replace('mm',''));cy=-float(r['Mid Y'].replace('mm',''))
 def transform(xy):x,y=xy;return cx+co*x-si*y,cy+si*x+co*y
 pads=[q for q in f.Pads() if q.GetNumber() and q.IsOnLayer(p.F_Cu)]
 if ref.startswith(('U501_','U502_')):
  nums=range(1,9) if ref.endswith('_L') else range(9,17)
  pads=[q for q in pads if int(q.GetNumber()) in nums]
  # These unkeyed socket strips have no polarity. Check all eight physical holes.
  pairs=[(n,xy,transform(xy),pads) for n,ps in v['pads'].items() for xy in ps]
 else:
  pairs=[]
  for n,ps in v['pads'].items():
   targets=[q for q in pads if q.GetNumber()==n]
   if ref.startswith('Q') and code=='C86513' and n in ['5','6','7','8']:targets=[q for q in pads if q.GetNumber()=='5']
   if ref=='J201':
    names={'A1B12':['A1','B12'],'B1A12':['B1','A12'],'B4A9':['B4','A9'],'A4B9':['A4','B9']}.get(n,[n])
    targets=[q for q in pads if q.GetNumber() in names] if n not in ['1','2','3','4'] else [q for q in pads if q.GetNumber()=='S1']
   if ref=='F1':targets=pads # Unpolarized two-clip holder; supplier numbers four holes, KiCad numbers two contacts.
   assert targets,(ref,n)
   for xy in ps:pairs.append((n,xy,transform(xy),targets))
 ds=[];outside=[];allpts=[]
 for n,xy,(xx,yy),targets in pairs:
  allpts.append((n,xx,yy))
  ds.append(min(math.hypot(xx-p.ToMM(q.GetPosition().x),yy-p.ToMM(q.GetPosition().y)) for q in targets))
  pt=p.VECTOR2I(p.FromMM(xx),p.FromMM(yy));shape=p.SHAPE_CIRCLE(pt,p.FromMM(.003))
  if not any(p.SHAPE.Collide(q.GetEffectiveShape(p.F_Cu),shape,0) for q in targets):outside.append(n)
 maxerr=max(ds);status='Supplier pad centers land on corresponding PCB copper'
 note='Same clockwise-screen transform for all parts: supplier SVG rotated by minus CPL angle.'
 if base in ['K501','K502']:
  status='Rotation agrees; supplier hole drawing conflicts with manufacturer';note='Supplier COM-to-coil-row offset is 2.55 mm; Omron specifies 2.00 mm and PCB agrees. Do not move holes to supplier CAD. Assembler must use the manufacturer drawing to align the physical relay; CPL origin is not certified by this malformed supplier pad pattern.'
 elif outside:
  status='Review pad/land overlap';note+=' Supplier center outside native copper: '+','.join(outside)
 if ref=='D2':note+=' Pin 1 LOWER-RIGHT; left leads +BATT, right leads/EP GND. TI land pattern uses 1.95 mm row centers versus supplier preview 2.0574 mm; matching orientation and overlapping lands.'
 if ref.startswith('J60'):note+=' Pin 1 LEFT on top view; MIN for J601–604, +5V for J605–606. Supplier pin1 is right at zero rotation; CPL180 reverses it correctly.'
 if ref=='U601':note+=' Pin 1 UPPER-LEFT. Supplier zero-angle pin1 is lower-left; CPL270 maps it to upper-left.'
 if ref=='F1':note+=' Unpolarized holder; four holes match two clips. Actual blade fuse is separate.'
 if code=='C27438':note+=' 1.0 mm PCB drills; unkeyed 1x8 strips are electrically symmetric under 180-degree reversal.'
 results.append(dict(ref=ref,sku=code,rotation=angle,x=cx,y=cy,supplier_pad_centers=len(pairs),max_same_pin_center_residual_mm=round(maxerr,6),centers_outside_native_copper=outside,status=status,note=note,source=v.get('source','Oct19 cached supplier footprint')))
 # One annotated overlay for each SKU + orientation; every connector position is included separately.
 key=(code,angle) if not ref.startswith('J') else ref
 if key in seen:continue
 seen.add(key)
 xs=[xx for n,xx,yy in allpts]+[p.ToMM(q.GetPosition().x) for q in pads];ys=[yy for n,xx,yy in allpts]+[p.ToMM(q.GetPosition().y) for q in pads]
 xmin,xmax=min(xs)-1.5,max(xs)+1.5;ymin,ymax=min(ys)-1.5,max(ys)+1.5
 scale=min(270/(xmax-xmin),190/(ymax-ymin));ox=15+(270-(xmax-xmin)*scale)/2;oy=44+(190-(ymax-ymin)*scale)/2
 def sx(x):return ox+(x-xmin)*scale
 def sy(y):return oy+(y-ymin)*scale
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="310" height="265" viewBox="0 0 310 265"><rect width="310" height="265" fill="#f5f7f9"/><text x="10" y="20" font-size="14">{html.escape(ref)} / {code} / CPL {angle:g}°</text><text x="10" y="36" font-size="10">TOP VIEW • gold: PCB lands • blue: supplier centers</text>']
 for q in pads:
  pos=q.GetPosition();sz=q.GetSize();w,h=p.ToMM(sz.x),p.ToMM(sz.y)
  if abs(q.GetOrientationDegrees()%180-90)<.1:w,h=h,w
  x,y=p.ToMM(pos.x),p.ToMM(pos.y)
  svg.append(f'<rect x="{sx(x-w/2):.2f}" y="{sy(y-h/2):.2f}" width="{w*scale:.2f}" height="{h*scale:.2f}" fill="#d4ad49" stroke="#806012" stroke-width=".5"/>')
 for n,x,y in allpts:
  svg.append(f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="2.5" fill="#1573be"/><text x="{sx(x)+4:.2f}" y="{sy(y)-3:.2f}" font-size="9" fill="#183252">{html.escape(n)}</text>')
 svg.append('</svg>');panels.append('<figure>'+''.join(svg)+'<figcaption>'+html.escape(note)+'</figcaption></figure>')
(OUT/'placements.json').write_text(json.dumps(results,indent=2)+'\n')
with open(OUT/'placements.csv','w') as ff:
 w=csv.DictWriter(ff,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
(OUT/'placement-overlays.html').write_text('<!doctype html><meta charset="utf-8"><title>ABX placement audit</title><style>body{font:14px sans-serif;margin:25px}main{display:flex;flex-wrap:wrap}figure{margin:8px;width:310px;border:1px solid #ccc}figcaption{padding:10px;font-size:11px;line-height:1.4}</style><h1>Supplier-to-PCB placement audit</h1><p>239 placements / 66 SKUs. Gold = native PCB copper bounding boxes; blue = numbered supplier pad centers. This checks placement geometry, not load/thermal qualification. Relay supplier CAD is inconsistent with Omron: resolve assembler origin against the manufacturer drawing.</p><main>'+''.join(panels)+'</main>')
assert before==hashlib.sha256(board.read_bytes()).hexdigest()
print('Placements',len(results),'SKUs',len({r['sku'] for r in results}),'overlay panels',len(panels))
for r in results:
 if r['status']!='Supplier pad centers land on corresponding PCB copper': print(r['ref'],r['status'],r['centers_outside_native_copper'],r['max_same_pin_center_residual_mm'])
