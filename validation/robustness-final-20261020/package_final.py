"""Package the checked Rev1.1c candidate. No board routing or source regeneration."""
from pathlib import Path
import csv,json,zipfile,hashlib,shutil,math,xml.etree.ElementTree as E
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];PROD=ROOT/'production/rev-1.1c-20261020';OLD=ROOT/'production/rev-1.1b-20261020';SUP=ROOT/'validation/assembly-audit-20261020/supplier';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
audit=json.load(open(OUT/'audit.json'));assert sha(ROOT/'abx-motion.kicad_pcb')==audit['PCB_sha256'];assert audit['ERC_violations']==audit['DRC_errors']==audit['unconnected_items']==audit['schematic_parity']==0
comp=json.load(open(OUT/'export-comparison.json'));assert len(comp)==13 and {k for k,v in comp.items() if not v}=={'abx-motion-F_Silkscreen.gto','abx-motion-B_Silkscreen.gbo'}
for name in ['review.txt','audit.json','changes.json','current-corners.json','blanking-sensitivity.json','loss-estimates.json','export-comparison.json','erc.json','drc.json','bench-procedure.txt','bench-results.csv']:shutil.copy2(OUT/name,PROD/name)
(PROD/'DO_NOT_ORDER.txt').unlink(missing_ok=True)
(PROD/'PROTOTYPE_STATUS.txt').write_text('PROTOTYPE FABRICATION CANDIDATE — CAD checks pass.\nConfirm relay physical alignment with JLCPCB before assembly.\nPhysical motor/thermal/fault tests require the first prototype boards and are NOT RUN.\nFull-power operation and return-energy/protection envelope remain unqualified.\nSee review.txt and bench-procedure.txt; bench-results.csv remains NOT RUN.\n')
# Preserve supplier placement evidence; replace only the resistor identity entries.
placements=json.load(open(OLD/'placements.json'))
for r in placements:
 if r['ref'] in ['R302','R402']:
  r['sku']='C22790';r['source']='validation/robustness-final-20261020/datasheets/C22790-1.svg';r['note']='12k / 0603 replacement. Native position and CPL angle unchanged. Both supplier numbered pad centers verified on matching native copper by audit_robustness.py.'
(PROD/'placements.json').write_text(json.dumps(placements,indent=2)+'\n')
with open(PROD/'placements.csv','w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(placements[0]));w.writeheader();w.writerows(placements)
s=(OLD/'placement-overlays.html').read_text().replace('C22984','C22790');(PROD/'placement-overlays.html').write_text(s)
for name in ['placement-summary.svg','placement-summary.png','assembly-D2-pinmap.svg']:shutil.copy2(OLD/name,PROD/name)
gs=sorted(p for p in (PROD/'gerbers').iterdir() if p.suffix!='.gbrjob');assert len(gs)==13 and {p.suffix for p in gs}>={'.drl','.gtl','.gbl','.g1','.g2'}
with zipfile.ZipFile(PROD/'abx-motion-gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in gs:z.write(f,f.name)
bom=list(csv.DictReader(open(PROD/'abx-motion-jlcpcb-bom.csv')));cpl=list(csv.DictReader(open(PROD/'abx-motion-jlcpcb-cpl.csv')));refs={r for row in bom for r in row['Designator'].split(',')};assert refs=={r['Designator'] for r in cpl} and len(refs)==239 and len(bom)==66
for row in bom:
 if {'R302','R402'} & set(row['Designator'].split(',')):assert row['Comment']=='12k' and row['LCSC Part #']=='C22790'
# Source bundle carries the exact saved design, custom libraries and reproducible audit evidence.
sources=list(ROOT.glob('*.kicad_sch'))+list(ROOT.glob('*.kicad_sym'))+[ROOT/n for n in ['abx-motion.kicad_pcb','abx-motion.kicad_pro','README.md','generate_schematics.py','robustness_support.py','fp-lib-table','sym-lib-table']]
for folder in ['abx-footprints.pretty','3dmodels']:sources += [p for p in (ROOT/folder).rglob('*') if p.is_file()]
evidence=[p for p in OUT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.html')]
# Add current supplier footprint data for every BOM SKU, replacing the old30k.
for code in {row['LCSC Part #'] for row in bom}:
 if code=='C22790':continue
 f=SUP/(code+'-1.svg');assert f.exists();evidence.append(f)
evidence += [SUP/'provenance.json',ROOT/'validation/assembly-audit-20261020/check_placements.py']
exports=[p for p in PROD.rglob('*') if p.is_file() and p.name not in ['manifest.json','abx-motion-review-bundle.zip']]
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(sources+evidence+exports))};(PROD/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(PROD/'abx-motion-review-bundle.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sources:z.write(p,'source/'+str(p.relative_to(ROOT)))
 for p in set(evidence):z.write(p,'evidence/'+str(p.relative_to(ROOT/'validation')))
 for p in exports:
  if p.parent==PROD:z.write(p,p.name)
 z.write(PROD/'manifest.json','manifest.json')
with zipfile.ZipFile(PROD/'abx-motion-review-bundle.zip') as z:
 assert z.testzip() is None
 assert hashlib.sha256(z.read('source/abx-motion.kicad_pcb')).hexdigest()==audit['PCB_sha256']
 assert z.read('abx-motion-jlcpcb-bom.csv')==(PROD/'abx-motion-jlcpcb-bom.csv').read_bytes()
assert all(sha(ROOT/f)==h for f,h in manifest.items())
for name in ['abx-motion-jlcpcb-bom.csv','abx-motion-bom.csv','JLCPCB_BOM.csv']:shutil.copy2(PROD/'abx-motion-jlcpcb-bom.csv',ROOT/'production'/name)
for name in ['abx-motion-jlcpcb-cpl.csv','abx-motion-cpl.csv','JLCPCB_CPL.csv']:shutil.copy2(PROD/'abx-motion-jlcpcb-cpl.csv',ROOT/'production'/name)
for name in ['abx-motion-gerbers.zip','abx-motion-v1.1-gerbers.zip','abx-motion-rev1.1c-gerbers.zip']:shutil.copy2(PROD/'abx-motion-gerbers.zip',ROOT/'production'/name)
for p in (PROD/'gerbers').iterdir():shutil.copy2(p,ROOT/'production/gerbers'/p.name)
for name in ['review.txt','abx-motion-review-bundle.zip']:shutil.copy2(PROD/name,ROOT/'production'/name)
for side in ['top','bottom']:
 for dest in [ROOT/f'renders/pcb_3d_{side}.png',ROOT/f'production/pcb_3d_{side}.png']:shutil.copy2(PROD/f'pcb_3d_{side}.png',dest)
for dest in [ROOT/'abx-motion-schematics.pdf',ROOT/'production/abx-motion-schematics.pdf']:shutil.copy2(PROD/'abx-motion-schematics.pdf',dest)
for name in ['erc.json','drc.json']:shutil.copy2(OUT/name,ROOT/name)
(ROOT/'production/LATEST.txt').write_text('Latest matched REVIEW candidate: rev-1.1c-20261020/\nHardware ABX-Motion Rev 1.1c. R302/R402=12k; nominal DC chop9.35 A.\nDesign checks PASS; physical motor/thermal/stall/regeneration tests NOT RUN.\nPrototype fabrication candidate. Confirm relay alignment before assembly. Full-power/return-energy qualification follows prototype receipt.\nSee review.txt, bench-procedure.txt and the NOT RUN bench-results.csv.\nUse matching Gerber/BOM/CPL. Changes remain local and uncommitted.\n')
print('Packaged:',PROD);print('BOM groups66 / placements239 / functional checks150 / pin nets751.');print('Current limit nominal9.35 A; no routing, pad or hole changes.');print('Prototype candidate packaged; relay assembly review pending; physical qualification NOT RUN.')
