"""Package exact audited thermal revision; never regenerates the board."""
from pathlib import Path
import json,hashlib,shutil,zipfile,csv
R=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent;P=R/'production/rev-1.1d-20261020';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
a=json.loads((O/'audit.json').read_text());assert sha(R/'abx-motion.kicad_pcb')==a['PCB_sha256']
for n in ['audit.json','review.txt','changes.json','drc.json','erc.json']:shutil.copy2(O/n,P/n)
f=P/'bench-procedure.txt';s=f.read_text().replace('Rev 1.1c','Rev 1.1d');s+='''\nESP32 / 3.3V THERMAL CHECK (Rev1.1d)\n\nAfter unloaded rail and firmware checks, run sustained Wi-Fi traffic plus\nCPU workload with motors disabled. Log U3 shield, U2 case, ambient and3.3V\nrail until temperatures settle or a commissioning stop threshold is reached.\nUse the earlier conservative70C case stop threshold; no temperature rating\nis established by this test procedure. Recheck with the intended external\n3.3V load and then during staged motor operation. Note resets/radio faults\nand rail droop. The ESP32 thermal pad already has12 plated holes.\n''';f.write_text(s)
f=P/'bench-results.csv';rows=list(csv.DictReader(open(f)));fields=list(rows[0]);
for name in ['ESP32 sustained Wi-Fi and CPU: U3/U2/3V3 thermal','Combined ESP32 activity and staged motor thermal']:
 if not any(row['Test']==name for row in rows):rows.append({**{k:'' for k in fields},'Test':name,'Status':'NOT RUN','Notes':'Record ambient, U3 shield and U2 case temperature in Notes.'})
with open(f,'w',newline='') as out:w=csv.DictWriter(out,fieldnames=fields);w.writeheader();w.writerows(rows)
(P/'PROTOTYPE_STATUS.txt').write_text('Rev1.1d prototype fabrication candidate: CAD checks pass.\nConfirm relay alignment before JLCPCB assembly.\nPowered motor/thermal/fault and return-energy qualification NOT RUN.\nUse the matching Rev1.1d Gerbers/BOM/CPL together.\n')
gs=sorted(x for x in (P/'gerbers').iterdir() if x.suffix!='.gbrjob');assert len(gs)==13
with zipfile.ZipFile(P/'abx-motion-gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in gs:z.write(f,f.name)
# Bundle exact saved native sources plus current and previous review evidence.
sources=[*R.glob('*.kicad_sch'),*R.glob('*.kicad_sym')]+[R/n for n in ['abx-motion.kicad_pcb','abx-motion.kicad_pro','README.md','generate_schematics.py','robustness_support.py','fp-lib-table','sym-lib-table']]
for folder in ['abx-footprints.pretty','3dmodels']:sources += [x for x in (R/folder).rglob('*') if x.is_file()]
evidence=[x for x in O.rglob('*') if x.is_file() and '__pycache__' not in x.parts]
evidence += [R/'validation/robustness-final-20261020'/n for n in ['audit.json','review.txt','netlist.xml','current-corners.json','blanking-sensitivity.json','loss-estimates.json']]
evidence += [x for x in (R/'validation/assembly-audit-20261020/supplier').glob('*.svg')]
evidence += [R/'validation/robustness-final-20261020/datasheets/C22790-1.svg',R/'validation/assembly-audit-20261020/supplier/provenance.json']
exports=[x for x in P.rglob('*') if x.is_file() and x.name not in ['manifest.json','abx-motion-review-bundle.zip']]
manifest={str(f.relative_to(R)):sha(f) for f in sorted(set(sources+evidence+exports))};(P/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(P/'abx-motion-review-bundle.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sources:z.write(f,'source/'+str(f.relative_to(R)))
 for f in evidence:z.write(f,'evidence/'+str(f.relative_to(R/'validation')))
 for f in exports:z.write(f,'exports/'+str(f.relative_to(P)))
 z.write(P/'manifest.json','manifest.json')
with zipfile.ZipFile(P/'abx-motion-review-bundle.zip') as z:
 assert z.testzip() is None;assert hashlib.sha256(z.read('source/abx-motion.kicad_pcb')).hexdigest()==a['PCB_sha256']
assert all(sha(R/f)==h for f,h in manifest.items())
for n in ['abx-motion-gerbers.zip','abx-motion-v1.1-gerbers.zip','abx-motion-rev1.1d-gerbers.zip']:shutil.copy2(P/'abx-motion-gerbers.zip',R/'production'/n)
for n in ['abx-motion-jlcpcb-bom.csv','abx-motion-bom.csv','JLCPCB_BOM.csv']:shutil.copy2(P/'abx-motion-jlcpcb-bom.csv',R/'production'/n)
for n in ['abx-motion-jlcpcb-cpl.csv','abx-motion-cpl.csv','JLCPCB_CPL.csv']:shutil.copy2(P/'abx-motion-jlcpcb-cpl.csv',R/'production'/n)
for f in (P/'gerbers').iterdir():shutil.copy2(f,R/'production/gerbers'/f.name)
for n in ['review.txt','abx-motion-review-bundle.zip','abx-motion-schematics.pdf','pcb_3d_top.png','pcb_3d_bottom.png']:shutil.copy2(P/n,R/'production'/n)
shutil.copy2(P/'abx-motion-schematics.pdf',R/'abx-motion-schematics.pdf')
for side in ['top','bottom']:shutil.copy2(P/f'pcb_3d_{side}.png',R/f'renders/pcb_3d_{side}.png')
for n in ['erc.json','drc.json']:shutil.copy2(O/n,R/n)
(R/'production/LATEST.txt').write_text('Latest matched prototype candidate: rev-1.1d-20261020/\nABX-Motion Rev1.1d: incremental thermal copper and20 tented vias.\nERC0; DRC0 errors/0 opens/0 parity;19 existing library warnings.\nBOM66groups/239placements; coordinates and angles unchanged.\nConfirm relay alignment before assembly. Physical qualification NOT RUN.\nUse the matching Gerber/BOM/CPL together; see review.txt.\nChanges are local and uncommitted; no Git push performed.\n')
print('Matched Rev1.1d Gerbers/BOM/CPL, native review bundle and manifest verified.');print('PCB SHA256',a['PCB_sha256'])
