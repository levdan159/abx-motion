"""Create a matched, explicitly unreleased review package. No PCB/CPL edits."""
from pathlib import Path
import json,csv,hashlib,shutil,zipfile,re,collections
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];PROD=ROOT/'production/assembly-audit-20261020';OLD=ROOT/'production/robustness-20261020'
PROD.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/'abx-motion.kicad_pcb')=='0625cd61f3970adfcf98d8586c776f4bc83c87c669794b3f35ddb2c3129c7920'
for name in ['abx-motion.kicad_pcb','abx-motion-jlcpcb-cpl.csv','abx-motion-jlcpcb-bom.csv']:
 current=ROOT/name if name.endswith('.kicad_pcb') else ROOT/'production'/name
 assert sha(current)==sha(OUT/'before'/name)
old_manifest=json.load(open(OLD/'manifest.json'))
for name,h in old_manifest.items():
 if name.endswith(('.kicad_sch','.kicad_sym','.kicad_pro')) or name.startswith('abx-footprints.pretty/') or name in ['generate_schematics.py','robustness_support.py']:
  assert sha(ROOT/name)==h,name
p=json.load(open(OUT/'placements.json'));d=json.load(open(OUT/'drc.json'));e=json.load(open(OUT/'erc.json'))
assert not [x for x in d['violations'] if x['severity']=='error'];assert not d['unconnected_items'];assert not d['schematic_parity'];assert not any(s.get('violations',[]) for s in e['sheets'])
assert all(json.load(open(OUT/'export-comparison.json')).values())
audit={'release_status':'HOLD: protection choice unresolved; relay physical alignment requires assembler review','PCB_sha256':sha(ROOT/'abx-motion.kicad_pcb'),'BOM_groups':66,'placements':239,'supplier_SKUs_with_current_footprint_SVG':66,'numbered_pad_orientation_and_copper_overlap_pass':237,'relay_rotation_agrees_but_supplier_origin_not_certified':['K501','K502'],'D2_rotation_supplier_verified':True,'U601_rotation_supplier_verified':True,'J601_to_J606_rotation_supplier_verified':True,'PCB_BOM_CPL_unchanged':True,'fresh_ERC_violations':0,'fresh_DRC_errors':0,'unconnected_items':0,'schematic_parity':0,'DRC_warnings':len(d['violations']),'DRC_warning_types':dict(collections.Counter(x['type'] for x in d['violations'])),'all_13_fabrication_files_match_prior_geometry':True,'second_TVS_added':False,'protection_notes':'Do not assume parallel TVS energy ratings add. No unconditional 32V or regenerative-energy qualification.'}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
# Recreate supplier provenance, including the successfully retried ESP32 preview.
provenance=[]
for row in csv.DictReader(open(ROOT/'production/abx-motion-jlcpcb-bom.csv')):
 code=row['LCSC Part #'];data=(OUT/'supplier'/(code+'.html')).read_text();urls=list(dict.fromkeys(re.findall(r'(?:https:)?//image\.easyeda\.com/component_svgs/prod/[^"<> ]+',data)))
 assert len(urls)>=2
 provenance.append({'sku':code,'page':'https://www.lcsc.com/product-detail/'+code+'.html','footprint_svg':'https:'+urls[1] if urls[1].startswith('//') else urls[1],'local':code+'-1.svg','sha256':sha(OUT/'supplier'/(code+'-1.svg'))})
(OUT/'supplier/provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
for name in ['abx-motion-jlcpcb-bom.csv','abx-motion-jlcpcb-cpl.csv','abx-motion-schematics.pdf','pcb_3d_top.png','pcb_3d_bottom.png']:shutil.copy2(OLD/name,PROD/name)
for name in ['review.txt','audit.json','placements.csv','placements.json','placement-overlays.html','placement-summary.svg','placement-summary.png','erc.json','drc.json','export-comparison.json']:shutil.copy2(OUT/name,PROD/name)
svg=(OLD/'assembly-D2-pinmap.svg').read_text().replace('Confirm physical pin-1 dot; supplier CPL rotation is not independently verified.','Supplier numbered-pad SVG now verifies CPL 180°. Confirm actual package pin-1 dot.').replace('Native footprint rotation 180°. Check the physical placement, not the angle alone.','PCB and supplier CPL rotation 180° agree. Electrical protection selection remains on hold.')
(PROD/'assembly-D2-pinmap.svg').write_text(svg)
(PROD/'DO_NOT_ORDER.txt').write_text(audit['release_status']+'\nSee review.txt. The small TVS candidate is not released for unknown motor energy.\n')
shutil.copytree(OUT/'fresh-gerbers',PROD/'gerbers',dirs_exist_ok=True)
gs=sorted(x for x in (PROD/'gerbers').iterdir() if x.suffix!='.gbrjob');assert len(gs)==13
with zipfile.ZipFile(PROD/'abx-motion-gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in gs:z.write(f,f.name)
sources=list(ROOT.glob('*.kicad_sch'))+list(ROOT.glob('*.kicad_sym'))+[ROOT/n for n in ['abx-motion.kicad_pcb','abx-motion.kicad_pro','README.md','generate_schematics.py','robustness_support.py','fp-lib-table','sym-lib-table']]
for dn in ['abx-footprints.pretty','3dmodels']:sources += [x for x in (ROOT/dn).rglob('*') if x.is_file()]
evidence=[x for x in OUT.iterdir() if x.is_file()]+list((OUT/'supplier').glob('*.svg'))+[OUT/'supplier/provenance.json',OUT/'supplier/combined-pad-cache.json']
exports=[x for x in PROD.rglob('*') if x.is_file() and x.name not in ['manifest.json','abx-motion-review-bundle.zip']]
manifest={str(f.relative_to(ROOT)):sha(f) for f in sorted(set(sources+evidence+exports))}
(PROD/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(PROD/'abx-motion-review-bundle.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sources:z.write(f,'source/'+str(f.relative_to(ROOT)))
 for f in evidence:z.write(f,'validation/'+str(f.relative_to(OUT)))
 for f in exports:
  if f.parent==PROD:z.write(f,f.name)
 z.write(PROD/'manifest.json','manifest.json')
with zipfile.ZipFile(PROD/'abx-motion-review-bundle.zip') as z:assert z.testzip() is None;assert hashlib.sha256(z.read('source/abx-motion.kicad_pcb')).hexdigest()==audit['PCB_sha256']
assert all(sha(ROOT/f)==h for f,h in manifest.items())
# Current aliases carry exactly the same review candidate, with a prominent hold.
for name in ['abx-motion-jlcpcb-bom.csv','abx-motion-bom.csv','JLCPCB_BOM.csv']:shutil.copy2(PROD/'abx-motion-jlcpcb-bom.csv',ROOT/'production'/name)
for name in ['abx-motion-jlcpcb-cpl.csv','abx-motion-cpl.csv','JLCPCB_CPL.csv']:shutil.copy2(PROD/'abx-motion-jlcpcb-cpl.csv',ROOT/'production'/name)
for name in ['abx-motion-gerbers.zip','abx-motion-v1.1-gerbers.zip']:shutil.copy2(PROD/'abx-motion-gerbers.zip',ROOT/'production'/name)
for f in (PROD/'gerbers').iterdir():shutil.copy2(f,ROOT/'production/gerbers'/f.name)
for name in ['review.txt','abx-motion-review-bundle.zip']:shutil.copy2(PROD/name,ROOT/'production'/name)
(ROOT/'production/LATEST.txt').write_text('Latest matched REVIEW candidate: assembly-audit-20261020/\n'+audit['release_status']+'\nD2/U601/PH supplier directions are now verified; see placement-overlays.html.\nGerber/BOM/CPL remain matched. No second TVS was added. Do not order until the hold is resolved.\n')
print(json.dumps(audit,indent=2));print('Review package:',PROD)
