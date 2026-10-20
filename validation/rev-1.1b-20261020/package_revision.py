"""Package the Rev 1.1b markings without regenerating or routing native design."""
from pathlib import Path
import json,shutil,zipfile,hashlib
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];PROD=ROOT/'production/rev-1.1b-20261020';OLD=ROOT/'production/assembly-audit-20261020';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inv=json.load(open(OUT/'electrical-invariants.json'));assert sha(ROOT/'abx-motion.kicad_pcb')==inv['PCB_sha256'];assert inv['only_silkscreen_manufacturing_geometry_changed']
d=json.load(open(OUT/'drc.json'));e=json.load(open(OUT/'erc.json'))
assert not any(v['severity']=='error' for v in d['violations']) and not d['unconnected_items'] and not d['schematic_parity']
assert not any(s.get('violations',[]) for s in e['sheets'])
for name in ['abx-motion-jlcpcb-bom.csv','abx-motion-jlcpcb-cpl.csv','placements.csv','placements.json','placement-overlays.html','placement-summary.svg','placement-summary.png','assembly-D2-pinmap.svg','DO_NOT_ORDER.txt']:shutil.copy2(OLD/name,PROD/name)
audit=json.load(open(OLD/'audit.json'));audit.update(revision='1.1b',PCB_sha256=inv['PCB_sha256'],revision_marking_changes_only=True,all_13_fabrication_files_match_prior_geometry=False,manufacturing_geometry_changes=['F.SilkS','B.SilkS'],copper_mask_paste_outline_drills_identical=True,git_local_HEAD='fc0f218bbfa59e0c1e870612c8e356da72eb1b0a',git_remote_HEAD_verified='fc0f218bbfa59e0c1e870612c8e356da72eb1b0a',current_changes_committed=False,current_changes_pushed=False)
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
review='''ABX-Motion Rev 1.1b — hardware revision marking / manufacturing review
20 October 2026

HOLD: protection choice unresolved; relay physical alignment requires assembler review.
No second TVS was added. This revision identifier is not manufacturing approval.

REVISION IDENTIFICATION

Use ABX-Motion Rev 1.1b for the hardware. Rev identifies the PCB revision;
firmware can use its own version numbering. This identifies the recent ADC
and resistor robustness changes, socket/BOM corrections and assembly review.

This pass updates the front and rear silkscreen model/revision labels and
rear specification-table heading. The heading font is reduced from 1.05 to
0.95 mm to retain its original table width. All text positions, logos and
copper artwork are preserved. Matching rear-library text and six schematic
title blocks now identify revision 1.1b. Generator revision metadata and
README are updated without running legacy layout/regeneration scripts.

FRESH VALIDATION

ERC: 0 violations including warnings.
DRC: 0 errors, 0 opens, 0 schematic parity issues; 19 existing library warnings.
751 schematic pin/net assignments match the prior validated source exactly.
Native PCB bytes are unchanged except the three text labels, header font,
rear footprint description and title metadata. Schematic changes are title
metadata only. Gerber comparison proves all copper, mask, paste, outline
and drill geometry identical; only F.SilkS and B.SilkS geometry changed.
BOM and CPL are copied byte-for-byte from the supplier-audited candidate:
66 part-number groups, 239 placements. Placement directions and positions
are unchanged. The complete supplier audit is included as a baseline report.

GIT STATE CHECKED THIS PASS

Branch: v1.1-final
Local committed HEAD: fc0f218bbfa59e0c1e870612c8e356da72eb1b0a
Live GitHub refs/heads/v1.1-final: same commit, verified read-only.
The robustness changes, assembly audit, regenerated manufacturing files and
Rev 1.1b markings remain local and uncommitted. They have not been pushed.
Matching committed branch heads do not mean the current working board is
backed up on GitHub. No commit, reset, branch rename or push was performed.

OPEN MANUFACTURING ISSUES

The small TVS3300 footprint and CPL direction are verified, but its 125 W
10/1000 us pulse rating replaces the larger SMCJ family's 1500 W rating.
The old SMCJ30A also had a 30 V standoff / 48.4 V maximum specified clamp,
which did not establish the requested normal-32 V / DRV8701 protection.
Direct parallel population does not guarantee sharing or add energy ratings.
Protection selection for unknown motor energy remains unresolved.
K501/K502 supplier CAD has a 2.55 mm COM-to-coil-row offset; manufacturer
and PCB use 2.00 mm. Confirm real-relay alignment against Omron's drawing.
See assembly-audit-baseline.txt for exact coordinates, limits and references.
Do not order this review candidate until these issues are resolved.

LATEST MATCHED FILES

production/rev-1.1b-20261020/abx-motion-gerbers.zip
production/rev-1.1b-20261020/abx-motion-jlcpcb-bom.csv
production/rev-1.1b-20261020/abx-motion-jlcpcb-cpl.csv
production/rev-1.1b-20261020/abx-motion-review-bundle.zip

Older dated directories are retained as history. Standard active aliases now
point to this review candidate, still on hold. Source and export hashes are
recorded in manifest.json; source is included in the review bundle.
'''
(OUT/'review.txt').write_text(review)
for name in ['review.txt','audit.json','erc.json','drc.json','change-scope.json','electrical-invariants.json']:shutil.copy2(OUT/name,PROD/name)
shutil.copy2(OLD/'review.txt',PROD/'assembly-audit-baseline.txt')
gs=sorted(p for p in (PROD/'gerbers').iterdir() if p.suffix!='.gbrjob');assert len(gs)==13
with zipfile.ZipFile(PROD/'abx-motion-gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in gs:z.write(p,p.name)
sources=list(ROOT.glob('*.kicad_sch'))+list(ROOT.glob('*.kicad_sym'))+[ROOT/n for n in ['abx-motion.kicad_pcb','abx-motion.kicad_pro','README.md','generate_schematics.py','robustness_support.py','fp-lib-table','sym-lib-table']]
for dn in ['abx-footprints.pretty','3dmodels']:sources += [p for p in (ROOT/dn).rglob('*') if p.is_file()]
evidence=[p for p in OUT.iterdir() if p.is_file()]+list((ROOT/'validation/assembly-audit-20261020/supplier').glob('*.svg'))+[ROOT/'validation/assembly-audit-20261020/supplier/provenance.json',ROOT/'validation/assembly-audit-20261020/check_placements.py']
exports=[p for p in PROD.rglob('*') if p.is_file() and p.name not in ['manifest.json','abx-motion-review-bundle.zip']]
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(sources+evidence+exports))};(PROD/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(PROD/'abx-motion-review-bundle.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sources:z.write(p,'source/'+str(p.relative_to(ROOT)))
 for p in evidence:z.write(p,'evidence/'+str(p.relative_to(ROOT/'validation')))
 for p in exports:
  if p.parent==PROD:z.write(p,p.name)
 z.write(PROD/'manifest.json','manifest.json')
with zipfile.ZipFile(PROD/'abx-motion-review-bundle.zip') as z:assert z.testzip() is None;assert hashlib.sha256(z.read('source/abx-motion.kicad_pcb')).hexdigest()==inv['PCB_sha256']
assert all(sha(ROOT/n)==h for n,h in manifest.items())
for name in ['abx-motion-jlcpcb-bom.csv','abx-motion-bom.csv','JLCPCB_BOM.csv']:shutil.copy2(PROD/'abx-motion-jlcpcb-bom.csv',ROOT/'production'/name)
for name in ['abx-motion-jlcpcb-cpl.csv','abx-motion-cpl.csv','JLCPCB_CPL.csv']:shutil.copy2(PROD/'abx-motion-jlcpcb-cpl.csv',ROOT/'production'/name)
for name in ['abx-motion-gerbers.zip','abx-motion-v1.1-gerbers.zip','abx-motion-rev1.1b-gerbers.zip']:shutil.copy2(PROD/'abx-motion-gerbers.zip',ROOT/'production'/name)
for p in (PROD/'gerbers').iterdir():shutil.copy2(p,ROOT/'production/gerbers'/p.name)
for name in ['review.txt','abx-motion-review-bundle.zip']:shutil.copy2(PROD/name,ROOT/'production'/name)
for side in ['top','bottom']:
 for dest in [ROOT/f'renders/pcb_3d_{side}.png',ROOT/f'production/pcb_3d_{side}.png']:shutil.copy2(PROD/f'pcb_3d_{side}.png',dest)
for dest in [ROOT/'abx-motion-schematics.pdf',ROOT/'production/abx-motion-schematics.pdf']:shutil.copy2(PROD/'abx-motion-schematics.pdf',dest)
for name in ['erc.json','drc.json']:shutil.copy2(OUT/name,ROOT/name)
(ROOT/'production/LATEST.txt').write_text('Latest matched REVIEW candidate: rev-1.1b-20261020/\nHardware: ABX-Motion Rev 1.1b\nHOLD: protection choice unresolved; relay physical alignment requires assembler review\nUse matching Gerber/BOM/CPL. No second TVS added.\nLatest changes are local and uncommitted; see review.txt for Git state.\n')
print('Packaged ABX-Motion Rev 1.1b:',PROD);print('PCB SHA256:',inv['PCB_sha256']);print('Release HOLD retained. Git working changes not committed or pushed.')
