from pathlib import Path
import shutil,json,hashlib
R=Path.cwd();V=R/'variants/ABX-Motion-ETH';W=R/'work/root-ethernet-promotion-20261024';B=W/'before';B.mkdir(exist_ok=True)
files={f.name:f for f in V.glob('*.kicad_sch')};files['abx-motion.kicad_sch']=files.pop('abx-motion-eth-placement.kicad_sch')
files.update({'abx-motion.kicad_pcb':V/'abx-motion-eth-placement.kicad_pcb','abx-motion.kicad_pro':V/'abx-motion-eth-placement.kicad_pro','ethernet-symbols.kicad_sym':V/'ethernet-symbols.kicad_sym','sym-lib-table':V/'sym-lib-table','fp-lib-table':V/'fp-lib-table'})
for folder in ['ethernet-footprints.pretty','models']:
 for p in (V/folder).iterdir():
  if p.is_file():files[f'{folder}/{p.name}']=p
# Back up user local settings as well as every replaced root file.
for rel in list(files)+['README.md','abx-motion.kicad_prl']:
 p=R/rel;q=B/rel
 if p.exists() and not q.exists():q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
manifest=[]
for rel,source in files.items():
 dest=R/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 if rel.endswith('.kicad_sch'):
  dest.write_text(source.read_text().replace('(project "abx-motion-eth-placement"','(project "abx-motion"'))
 elif rel.endswith('.kicad_pro'):
  d=json.loads(source.read_text());d['meta']['filename']='abx-motion.kicad_pro'
  for sheet in d['schematic'].get('top_level_sheets',[]):
   if sheet.get('filename')=='abx-motion-eth-placement.kicad_sch':sheet['filename']='abx-motion.kicad_sch';sheet['name']='abx-motion'
  dest.write_text(json.dumps(d,indent=2)+'\n')
 else:shutil.copy2(source,dest)
 manifest.append(dict(file=rel,source=str(source.relative_to(R)),sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
(W/'promotion-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Promoted',len(files),'files; original local .pro/.prl saved under',B)
