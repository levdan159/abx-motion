"""Package already checked saved files; never rebuild or route the board."""
from pathlib import Path
import hashlib,json,shutil,zipfile,csv
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
PROD=ROOT/'production/robustness-20261020'
audit=json.loads((OUT/'audit.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/'abx-motion.kicad_pcb')==audit['PCB_sha256']
assert audit['ERC_violations']==audit['DRC_errors']==audit['unconnected_items']==audit['schematic_parity']==0
assert audit['all_original_tracks_and_vias_preserved']
assert audit['all_other_footprints_including_logos_identical']
gerbers=sorted(p for p in (PROD/'gerbers').iterdir() if p.suffix!='.gbrjob')
assert len(gerbers)==13
assert {p.name for p in gerbers if p.suffix=='.drl'}=={'abx-motion-PTH.drl','abx-motion-NPTH.drl'}
for p in gerbers:assert p.stat().st_size>100
with zipfile.ZipFile(PROD/'abx-motion-gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in gerbers:z.write(p,p.name)
for name in ['review.txt','audit.json','erc.json','drc.json']:
    shutil.copy2(OUT/name,PROD/name)

# A top-view pin map for review in the assembler's editor (north = board top).
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="620" viewBox="0 0 800 620">',
 '<rect width="800" height="620" fill="#fff"/>',
 '<g font-family="sans-serif" fill="#17212b"><text x="36" y="40" font-size="25">D2 — TVS3300DRVR — required TOP-view orientation</text>',
 '<text x="36" y="70" font-size="17">XT60 is at the upper-right of the board. North ↑</text>',
 '<text x="36" y="100" font-size="16">Confirm physical pin-1 dot; supplier CPL rotation is not independently verified.</text>',
 '<rect x="250" y="175" width="300" height="300" fill="#dfe6eb" stroke="#17212b"/>',
 '<rect x="325" y="205" width="150" height="240" fill="#d8e9f8" stroke="#24679b"/>',
 '<text x="365" y="322" font-size="17">EP 7</text><text x="369" y="347" font-size="17">GND</text>']
for number,y in [(4,227),(5,325),(6,423)]:
    svg.append(f'<rect x="220" y="{y-22}" width="68" height="44" fill="#f5d471" stroke="#805c00"/><text x="240" y="{y+7}" font-size="22">{number}</text><text x="85" y="{y+7}" font-size="19">+BATT</text>')
for number,y in [(3,227),(2,325),(1,423)]:
    svg.append(f'<rect x="512" y="{y-22}" width="68" height="44" fill="#a5cceb" stroke="#24679b"/><text x="537" y="{y+7}" font-size="22">{number}</text><text x="610" y="{y+7}" font-size="19">GND</text>')
svg+=['<circle cx="505" cy="445" r="9" fill="#cf2424"/>',
 '<text x="36" y="525" font-size="20" fill="#b00020">Pin 1 must be LOWER-RIGHT: board X182.975, Y64.150 mm.</text>',
 '<text x="36" y="558" font-size="17">Pins 4/5/6 = +BATT. Pins 1/2/3 and exposed pad 7 = GND.</text>',
 '<text x="36" y="588" font-size="16">Native footprint rotation 180°. Check the physical placement, not the angle alone.</text></g></svg>']
(PROD/'assembly-D2-pinmap.svg').write_text('\n'.join(svg)+'\n')
shutil.copy2(PROD/'assembly-D2-pinmap.svg',OUT/'assembly-D2-pinmap.svg')

sources=list(ROOT.glob('*.kicad_sch'))+list(ROOT.glob('*.kicad_sym'))
sources += [ROOT/n for n in ['abx-motion.kicad_pcb','abx-motion.kicad_pro','README.md',
            'generate_schematics.py','robustness_support.py','fp-lib-table','sym-lib-table']]
for dn in ['abx-footprints.pretty','3dmodels']:
    sources.extend(p for p in (ROOT/dn).rglob('*') if p.is_file())
evidence=[OUT/n for n in ['audit.json','erc.json','drc.json','netlist.xml','review.txt',
            'sensing-changes.json','clamp-changes.json','local-sites.json',
            'apply_sensing.py','apply_clamp.py','find_local_sites.py','audit_final.py','package.py',
            'datasheets/tvs3300.pdf','before/abx-motion.kicad_pcb']]
export_files=[p for p in PROD.rglob('*') if p.is_file() and p.name not in ['manifest.json','abx-motion-review-bundle.zip']]
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(sources+evidence+export_files))}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
shutil.copy2(OUT/'manifest.json',PROD/'manifest.json')
with zipfile.ZipFile(PROD/'abx-motion-review-bundle.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sources:z.write(p,'source/'+str(p.relative_to(ROOT)))
    for p in evidence:z.write(p,'validation/'+str(p.relative_to(OUT)))
    for p in export_files:
        if p.parent==PROD:z.write(p,p.name)
    z.write(PROD/'manifest.json','manifest.json')
with zipfile.ZipFile(PROD/'abx-motion-review-bundle.zip') as z:
    assert z.testzip() is None
    assert hashlib.sha256(z.read('source/abx-motion.kicad_pcb')).hexdigest()==audit['PCB_sha256']
    assert 'source/robustness_support.py' in z.namelist()
assert all(sha(ROOT/n)==h for n,h in manifest.items())

# Refresh only documented active aliases. Preserve every historical package.
for name in ['abx-motion-jlcpcb-bom.csv','abx-motion-bom.csv','JLCPCB_BOM.csv']:
    shutil.copy2(PROD/'abx-motion-jlcpcb-bom.csv',ROOT/'production'/name)
for name in ['abx-motion-jlcpcb-cpl.csv','abx-motion-cpl.csv','JLCPCB_CPL.csv']:
    shutil.copy2(PROD/'abx-motion-jlcpcb-cpl.csv',ROOT/'production'/name)
for name in ['abx-motion-gerbers.zip','abx-motion-v1.1-gerbers.zip']:
    shutil.copy2(PROD/'abx-motion-gerbers.zip',ROOT/'production'/name)
for p in (PROD/'gerbers').iterdir():shutil.copy2(p,ROOT/'production/gerbers'/p.name)
for side in ['top','bottom']:
    for dest in [ROOT/f'renders/pcb_3d_{side}.png',ROOT/f'production/pcb_3d_{side}.png']:
        shutil.copy2(PROD/f'pcb_3d_{side}.png',dest)
for dest in [ROOT/'abx-motion-schematics.pdf',ROOT/'production/abx-motion-schematics.pdf']:
    shutil.copy2(PROD/'abx-motion-schematics.pdf',dest)
for name in ['review.txt','abx-motion-review-bundle.zip']:shutil.copy2(PROD/name,ROOT/'production'/name)
for name in ['erc.json','drc.json']:shutil.copy2(OUT/name,ROOT/name)
(ROOT/'production/LATEST.txt').write_text(
    'Latest matching prototype package: robustness-20261020/\n'
    'ASSEMBLY HOLD: approve new D2 physical pin-1 orientation in JLC before ordering.\n'
    'See assembly-D2-pinmap.svg and review.txt in that directory.\n'
    'Use its Gerber ZIP, BOM and CPL together; older uploads have different D2/ADC parts.\n'
    '32 V is the normal ceiling; local clamp handles rated short pulses, not sustained regeneration.\n'
    'No unrestricted battery/load operating qualification is claimed.\n')
print('Verified and packaged:',PROD)
print('BOM/CPL: 66 groups / 239 placements. Gerber ZIP: 11 layers + 2 drills.')
print('Assembly hold remains until D2 physical pin-1 is checked in JLC.')
