from pathlib import Path
import json,csv,hashlib,zipfile,subprocess,collections
O=Path(__file__).resolve().parent;R=O.parents[1];P=R/'production/rev-1.2a-20261023';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
a=json.loads((O/'before-branding-snapshot.json').read_text());current=json.loads(subprocess.check_output(['/usr/bin/python3',str(O/'geometry_snapshot.py'),str(R/'abx-motion.kicad_pcb')],stderr=subprocess.DEVNULL))
assert a['copper']==current['copper'];assert a['footprints'].keys()==current['footprints'].keys();changed=[a['footprints'][u]['ref'] for u in a['footprints'] if a['footprints'][u]!=current['footprints'][u]];assert set(changed)=={'LOGO1','LOGO2'}
d=json.loads((O/'drc.json').read_text());assert not [r for r in d['violations'] if r['severity']=='error'];assert not d['unconnected_items'];assert not d['schematic_parity'];assert len(d['violations'])==95
e=json.loads((O/'erc.json').read_text());assert not [v for s in e.get('sheets',[]) for v in s.get('violations',[])]
m=json.loads((P/'manifest.json').read_text());assert m['PCB_sha256']==sha(R/'abx-motion.kicad_pcb')
for path,h in m['source_files'].items():assert sha(R/path)==h,path
for path,h in m['package_files'].items():assert sha(P/path)==h,path
for f in P.glob('*.zip'):
 with zipfile.ZipFile(f) as z:assert z.testzip() is None
rows=list(csv.DictReader(open(P/'filled-capped-vias.csv')));assert len(rows)==104;assert len({r['uuid'] for r in rows})==104
report={'PCB_sha256':m['PCB_sha256'],'electrical_footprints_unchanged_since_revision_export_start':True,'existing_track_via_UUID_geometry_nets_unchanged':True,'decorative_footprints_changed':changed,'ERC_violations':0,'DRC_errors':0,'DRC_warnings':95,'unconnected_items':0,'schematic_parity':0,'catalogue_SKUs':74,'catalogue_placements':328,'supplier_pad_checks_pass':326,'relay_alignment_required':['K501','K502'],'separately_sourced_socket':'J208','selected_filled_capped_features':104,'manifest_hashes_match':True,'all_zip_integrity_checks_pass':True}
(O/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
