from pathlib import Path
import collections,hashlib,json,re,xml.etree.ElementTree as ET
import pcbnew
R=Path.cwd();V=R/'variants/ABX-Motion-ETH';O=R/'validation/root-ethernet-promotion-20261024'
normalize_models=lambda s:re.sub(r'\(model "[^"]+"','(model "MODEL"',s)
assert normalize_models((R/'abx-motion.kicad_pcb').read_text())==normalize_models((V/'abx-motion-eth-placement.kicad_pcb').read_text())
for src in V.glob('*.kicad_sch'):
 name='abx-motion.kicad_sch' if src.name=='abx-motion-eth-placement.kicad_sch' else src.name
 assert (R/name).read_text()==src.read_text().replace('(project "abx-motion-eth-placement"','(project "abx-motion"'),name
pro=json.loads((R/'abx-motion.kicad_pro').read_text());assert pro['meta']['filename']=='abx-motion.kicad_pro'
assert pro['schematic']['top_level_sheets'][0]['filename']=='abx-motion.kicad_sch'
assert pro['board']['design_settings']['rules']['min_clearance']==.15
assert pro['board']['design_settings']['rules']['min_track_width']==.15
expected={}
for net in ET.parse(O/'netlist.xml').findall('.//nets/net'):
 for node in net.findall('node'):expected[(node.get('ref'),node.get('pin'))]=net.get('name')
b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()}
for ref,f in fs.items():
 for p in f.Pads():
  if (ref,p.GetNumber()) in expected:assert p.GetNetname()==expected[(ref,p.GetNumber())],(ref,p.GetNumber())
missing=[]
for ref,f in fs.items():
 for model in f.Models():
  path=str(model.m_Filename).replace('${KIPRJMOD}',str(R))
  for ver in range(7,11):path=path.replace('${KICAD'+str(ver)+'_3DMODEL_DIR}','/usr/share/kicad/3dmodels')
  if not Path(path).is_file():missing.append((ref,path))
assert not missing,missing
j=json.loads((O/'drc.json').read_text());counts=collections.Counter(v['type'] for v in j['violations']);old=json.loads((R/'validation/ethernet-checkpoint-20261024/board-drc.json').read_text())
assert counts==collections.Counter(v['type'] for v in old['violations']);assert not j['unconnected_items']
assert len(j['schematic_parity'])==49 and all(v['type']=='extra_footprint' for v in j['schematic_parity'])
erc=json.loads((O/'erc.json').read_text());assert not any(s.get('violations') for s in erc.get('sheets',[]))
result=dict(status='Root project matches reviewed Ethernet development draft',root_pcb_sha256=hashlib.sha256((R/'abx-motion.kicad_pcb').read_bytes()).hexdigest(),pcb_geometry_unchanged_model_paths_may_be_localized=True,schematic_instances_renamed=True,project_metadata_renamed=True,all_mapped_pad_nets_match_fresh_netlist=True,missing_models=missing,erc_violations=0,defined_net_opens=0,expected_draft_parity_warnings=49,drc_counts=dict(counts),manufacturing_ready=False,rollback_commit='86024cc',local_settings_backup='work/root-ethernet-promotion-20261024/before/')
(O/'qa-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
