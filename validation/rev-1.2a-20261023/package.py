"""Package current PCB and audited assembly metadata. Does not modify the design."""
from pathlib import Path
import json,csv,collections,shutil,hashlib,zipfile,html,math,re
import pcbnew as p
O=Path(__file__).resolve().parent;ROOT=O.parents[1];P=ROOT/'production/rev-1.2a-20261023';P.mkdir(exist_ok=True)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
sel=json.loads((O/'selections.json').read_text());cat={r['code']:r for r in json.loads((O/'catalog-selected.json').read_text())};places=json.loads((O/'placements.json').read_text());inv={r['ref']:r for r in json.loads((O/'inventory.json').read_text())}
assert len(places)==len(sel)==328
assert sum(r['status']=='PASS' for r in places)==326
assert {r['ref'] for r in places if r['status']!='PASS'}=={'K501','K502'}
b=p.LoadBoard(str(ROOT/'abx-motion.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()}
assert all(next(q.GetText() for q in fs[r].GetFields() if q.GetName()=='LCSC')==code for r,code in sel.items())
def writecsv(path,fields,rows):
 with open(path,'w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
groups=collections.defaultdict(list)
for r,c in sel.items():groups[c].append(r)
bom=[]
for c,refs in sorted(groups.items()):
 cr=cat[c];fps={inv[r]['footprint'] for r in refs};assert len(fps)==1
 bom.append({'Comment':cr['componentModelEn'],'Designator':','.join(sorted(refs)),'Footprint':next(iter(fps)),'LCSC Part #':c,'Manufacturer':cr['componentBrandEn'],'MPN':cr['componentModelEn'],'Quantity':len(refs),'Value':' / '.join(sorted({inv[r]['value'] for r in refs}))})
writecsv(P/'abx-motion-rev1.2a-jlcpcb-bom.csv',list(bom[0]),bom)
cpl=[{'Designator':r['ref'],'Val':r['value'],'Package':r['footprint'],'Mid X':f'{r["x"]:.4f}mm','Mid Y':f'{-r["y"]:.4f}mm','Rotation':f'{r["rotation"]:.1f}','Layer':'Top'} for r in places]
writecsv(P/'abx-motion-rev1.2a-jlcpcb-cpl.csv',list(cpl[0]),cpl)
# Read back the actual upload files; check identity, count and coordinate rounding.
rb=list(csv.DictReader(open(P/'abx-motion-rev1.2a-jlcpcb-bom.csv')));rc=list(csv.DictReader(open(P/'abx-motion-rev1.2a-jlcpcb-cpl.csv')))
assert {r for row in rb for r in row['Designator'].split(',')}=={r['Designator'] for r in rc}==set(sel)
for r in rc:
 q=next(v for v in places if v['ref']==r['Designator']);assert float(r['Rotation'])==q['rotation'];assert abs(float(r['Mid X'][:-2])-q['x'])<.000051;assert abs(float(r['Mid Y'][:-2])+q['y'])<.000051
manual=[{'Designator':'J208','Quantity':1,'Part':'Samtec SLW-104-01-L-S','Reason':'Low-profile 4.57 mm body, 2.54 mm pitch socket; source separately or arrange JLC consignment. Unkeyed single row; preserve PCB pin labels. Confirm actual OLED header engagement at 10 mm standoff height.'},{'Designator':'JP701/JP702/JP703 shunts','Quantity':3,'Part':'2.54 mm two-position insulated jumper shunt','Reason':'Fit to ONBOARD positions for default onboard axis control; headers themselves are in assembly BOM.'},{'Designator':'F1 fuse element','Quantity':1,'Part':'Compatible blade fuse, chosen for actual wiring/load envelope','Reason':'F1 in JLC BOM is the holder only. Board 25 A marking is a design target, not a qualified assembly current rating.'},{'Designator':'OLED and standoffs','Quantity':1,'Part':'Actual OLED module, matching header, 10 mm insulating standoffs','Reason':'Confirm module hole spacing and plug engagement; OLED module is not a fitted PCB footprint part.'},{'Designator':'Heatsinks and TIM','Quantity':1,'Part':'Stock finned sinks and electrically insulating TIM; selection pending','Reason':'Do not order archived machined HS1. No selected installed cooling rating or heatsink SKU is approved by this package.'}]
writecsv(P/'manual-and-mechanical-bom.csv',list(manual[0]),manual)
j=fs['J208'];positions=[q.GetPosition() for q in j.Pads()];manualpos=[{'Designator':'J208','Mid X':f'{sum(p.ToMM(q.x) for q in positions)/len(positions):.4f}mm','Mid Y':f'{-sum(p.ToMM(q.y) for q in positions)/len(positions):.4f}mm','Native rotation':j.GetOrientationDegrees(),'Layer':'Top','Note':'Unkeyed manually fitted socket; not a JLC supplier-normalized CPL row.'}]
writecsv(P/'manual-placement.csv',list(manualpos[0]),manualpos)
writecsv(P/'catalogue-audit.csv',['LCSC Part #','MPN','Manufacturer','Package','Description','Assembly mode','Library','JLCPCB URL','Availability'],[{'LCSC Part #':c,'MPN':cat[c]['componentModelEn'],'Manufacturer':cat[c]['componentBrandEn'],'Package':cat[c]['componentSpecificationEn'],'Description':cat[c]['describe'],'Assembly mode':cat[c].get('assemblyMode',''),'Library':cat[c].get('componentLibraryType',''),'JLCPCB URL':f'https://jlcpcb.com/partdetail/Component/{c}','Availability':'Catalogue listing verified; live allocation/stock not reserved. Check at order quantity.'} for c in sorted(groups)])
for name in ['drc.json','erc.json','placements.csv','placements.json','catalog-selected.json','metadata-changes.json']:shutil.copy2(O/name,P/name)
shutil.copy2(ROOT/'design/thermal-rev1.2-20261023/filled-capped-vias.csv',P/'filled-capped-vias.csv')
(P/'README.txt').write_text('''ABX-Motion Rev 1.2a — JLCPCB prototype fabrication / assembly review package
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
''')
# Supplier overlay audit, native numbered lands and transformed supplier centers.
import xml.etree.ElementTree as E
panels=[];seen=set()
for r in places:
 ref,c=r['ref'],r['code'];key=ref if ref.startswith(('J','K')) else (c,r['rotation'])
 if key in seen:continue
 seen.add(key);f=fs[ref];pads=[q for q in f.Pads() if q.GetNumber() and q.IsOnLayer(p.F_Cu)];root=E.parse(O/'supplier'/f'{c}-1.svg').getroot();g=next(g for g in root if 'c_para' in g.attrib);ox,oy=map(float,g.attrib['c_origin'].split(','));co=math.cos(math.radians(-r['rotation']));si=math.sin(math.radians(-r['rotation']));points=[]
 for e in g.iter():
  if e.attrib.get('c_partid')=='part_pad':
   xx,yy=map(float,e.attrib['c_origin'].split(','));x,y=(xx-ox)*.254,(yy-oy)*.254;points.append((e.attrib['number'],r['x']+co*x-si*y,r['y']+si*x+co*y))
 xs=[x for _,x,y in points]+[p.ToMM(q.GetPosition().x) for q in pads];ys=[y for _,x,y in points]+[p.ToMM(q.GetPosition().y) for q in pads];xmin,xmax=min(xs)-1.5,max(xs)+1.5;ymin,ymax=min(ys)-1.5,max(ys)+1.5;scale=min(280/(xmax-xmin),190/(ymax-ymin));sx=lambda x:15+(x-xmin)*scale;sy=lambda y:45+(y-ymin)*scale
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="270"><rect width="320" height="270" fill="#f4f6f8"/><text x="10" y="20" font-size="13">{html.escape(ref)} / {c} / {r["rotation"]}°</text>']
 for q in pads:
  x,y=p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y);w,h=p.ToMM(q.GetSize().x),p.ToMM(q.GetSize().y)
  if abs(q.GetOrientationDegrees()%180-90)<.01:w,h=h,w
  svg.append(f'<rect x="{sx(x-w/2):.3f}" y="{sy(y-h/2):.3f}" width="{w*scale:.3f}" height="{h*scale:.3f}" fill="#dfbb59" stroke="#856000" stroke-width=".4"/>')
 for n,x,y in points:svg.append(f'<circle cx="{sx(x):.3f}" cy="{sy(y):.3f}" r="2" fill="#1060a5"/><text x="{sx(x)+3:.3f}" y="{sy(y)-2:.3f}" font-size="8">{html.escape(n)}</text>')
 svg.append('</svg>');panels.append('<figure>'+''.join(svg)+'<figcaption>'+html.escape(r['status'])+'</figcaption></figure>')
(P/'assembly/placement-overlays.html').write_text('<!doctype html><meta charset="utf-8"><title>Rev 1.2a placement audit</title><style>body{font:14px sans-serif;margin:24px}main{display:flex;flex-wrap:wrap}figure{margin:8px;border:1px solid #ccc}figcaption{padding:8px}</style><h1>Rev 1.2a supplier placement audit</h1><p>Top view. Gold: native PCB lands; blue: supplier numbered pad centers using exported CPL origins and rotations. All 328 placements audited; panels cover each SKU/angle and every connector/relay. Relays require manufacturer alignment review.</p><main>'+''.join(panels)+'</main>')
# Relay-specific physical pad drawing, independent of malformed supplier geometry.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="500" viewBox="0 0 1100 500"><rect width="1100" height="500" fill="white"/><text x="25" y="30" font-size="20">Rev 1.2a — relay alignment / TOP VIEW / native PCB hole positions</text>']
for idx,ref in enumerate(['K501','K502']):
 f=fs[ref];pads=list(f.Pads());xs=[p.ToMM(q.GetPosition().x) for q in pads];ys=[p.ToMM(q.GetPosition().y) for q in pads];xmin,ymin=min(xs),min(ys);ox=50+idx*530;oy=100;sc=17
 svg.append(f'<text x="{ox}" y="70" font-size="18">{ref} — Omron G5LE-14 5 V</text>')
 for q in pads:
  x,y=p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y);xx,yy=ox+(x-xmin)*sc,oy+(y-ymin)*sc
  svg.append(f'<circle cx="{xx}" cy="{yy}" r="10" fill="#dbb34b" stroke="black"/><text x="{xx+14}" y="{yy+5}" font-size="12">{html.escape(q.GetNumber())} {html.escape(q.GetNetname())}</text>')
 svg.append(f'<text x="{ox}" y="415" font-size="12">CPL rotation {next(r["rotation"] for r in places if r["ref"]==ref)}°; verify physical body origin against manufacturer drawing.</text>')
svg.append('<text x="25" y="465" font-size="13">Supplier preview has a 0.55 mm hole-offset discrepancy. Match actual relay leads to the numbered PCB holes; do not alter PCB holes.</text></svg>')
(P/'assembly/relay-alignment.svg').write_text(''.join(svg))
gs=sorted(f for f in (P/'gerbers').iterdir() if f.suffix!='.gbrjob');assert len(gs)==13
with zipfile.ZipFile(P/'abx-motion-rev1.2a-gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in gs:z.write(f,f.name)
for f in gs:
 if f.suffix=='.drl':assert 'M48' in f.read_text()
source=[*ROOT.glob('*.kicad_sch'),*ROOT.glob('*.kicad_sym'),*[ROOT/n for n in ['abx-motion.kicad_pcb','abx-motion.kicad_pro','fp-lib-table','sym-lib-table','README.md']]]
for folder in ['abx-footprints.pretty','3dmodels','abx-3dmodels']:source.extend(f for f in (ROOT/folder).rglob('*') if f.is_file())
source.extend([ROOT/'design/rev-1.2a-checkpoint.md',ROOT/'design/limit-inputs-rev1.2-20261023.txt',ROOT/'design/thermal-rev1.2-20261023.md'])
with zipfile.ZipFile(P/'abx-motion-rev1.2a-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in source:z.write(f,str(f.relative_to(ROOT)))
manifest={'hardware_revision':'Rev 1.2a','PCB_sha256':sha(ROOT/'abx-motion.kicad_pcb'),'source_files':{str(f.relative_to(ROOT)):sha(f) for f in source},'package_files':{str(f.relative_to(P)):sha(f) for f in P.rglob('*') if f.is_file() and f.name not in ['manifest.json','abx-motion-rev1.2a-jlcpcb-package.zip']},'catalogued_placements':328,'catalogue_SKUs':74,'placement_geometry_pass':326,'relay_alignment_review':['K501','K502'],'manufacturing_status':'Prototype fabrication and assembler review; physical qualification not run'}
(P/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(P/'abx-motion-rev1.2a-jlcpcb-package.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in P.rglob('*'):
  if f.is_file() and f.name!='abx-motion-rev1.2a-jlcpcb-package.zip':z.write(f,str(f.relative_to(P)))
for f in P.glob('*.zip'):
 with zipfile.ZipFile(f) as z:assert z.testzip() is None
print('Packaged',len(bom),'SKUs,',len(cpl),'JLC placements + separate J208; 326 pad checks PASS, 2 relay alignment reviews.')
