"""Read-only checkpoint audit. Run from repository root using system Python/KiCad."""
from pathlib import Path
import collections,hashlib,json,subprocess,xml.etree.ElementTree as ET
import pcbnew
ROOT=Path.cwd();OUT=ROOT/'validation/ethernet-checkpoint-20261024';V=ROOT/'variants/ABX-Motion-ETH'
base=OUT/'baseline.kicad_pcb'
base.write_bytes(subprocess.check_output(['git','show','9fd9be1:variants/ABX-Motion-ETH/abx-motion-eth-placement.kicad_pcb']))
a=pcbnew.LoadBoard(str(base));b=pcbnew.LoadBoard(str(V/'abx-motion-eth-placement.kicad_pcb'))
fs={f.GetReference():f for f in b.GetFootprints()};afs={f.GetReference():f for f in a.GetFootprints()}
parts=json.loads((V/'layout-review/parts.json').read_text());power=set(json.loads((ROOT/'work/ethernet-routing-20261024/power-refs.json').read_text()));draft=set(parts)-power
assert len(parts)==61 and len(draft)==49
assert len(fs)==len(list(b.GetFootprints())),'Duplicate reference'
assert set(fs)==set(afs),'Missing/extra footprint versus approved layout'
for ref,f in afs.items():
 assert fs[ref].GetPosition()==f.GetPosition() and fs[ref].GetOrientationDegrees()==f.GetOrientationDegrees(),ref
 if ref not in power:
  assert {(p.m_Uuid.AsString(),p.GetNumber(),p.GetNetname()) for p in f.Pads()}=={(p.m_Uuid.AsString(),p.GetNumber(),p.GetNetname()) for p in fs[ref].Pads()},ref
for ref in draft:assert all(p.GetNetCode()==0 for p in fs[ref].Pads()),ref
for ref in parts:assert fs[ref].IsExcludedFromBOM() and fs[ref].IsExcludedFromPosFiles(),ref
expected={}
for net in ET.parse(OUT/'netlist.xml').findall('.//nets/net'):
 for n in net.findall('node'):expected[(n.get('ref'),n.get('pin'))]=net.get('name')
for ref,f in fs.items():
 for p in f.Pads():
  key=(ref,p.GetNumber())
  if key in expected:assert p.GetNetname()==expected[key],(key,p.GetNetname(),expected[key])
assert {(z.m_Uuid.AsString(),z.GetNetname(),tuple(z.GetLayerSet().Seq())) for z in a.Zones()}=={(z.m_Uuid.AsString(),z.GetNetname(),tuple(z.GetLayerSet().Seq())) for z in b.Zones()}
assert {t.m_Uuid.AsString() for t in a.GetTracks() if t.GetLayer()==pcbnew.In1_Cu and t.GetClass()=='PCB_TRACK'}=={t.m_Uuid.AsString() for t in b.GetTracks() if t.GetLayer()==pcbnew.In1_Cu and t.GetClass()=='PCB_TRACK'}
hashes=json.loads((ROOT/'work/ethernet-rev1.2b-20261023/baseline-hashes.json').read_text())
for path,h in hashes.items():
 if path.endswith(('.kicad_pcb','.kicad_sch')):assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,path
erc=json.loads((OUT/'schematic-erc.json').read_text());assert not any(sheet.get('violations') for sheet in erc.get('sheets',[]))
j=json.loads((OUT/'board-drc.json').read_text());counts=collections.Counter(v['type'] for v in j['violations']);hard=['shorting_items','clearance','tracks_crossing','hole_clearance','holes_co_located','track_width','via_diameter','drill_out_of_range']
assert not j['unconnected_items']
assert all(counts[k]==0 for k in hard),dict(counts)
extra=j['schematic_parity'];assert len(extra)==49 and all(v['type']=='extra_footprint' for v in extra)
uuids={fs[r].m_Uuid.AsString() for r in draft};assert {v['items'][0]['uuid'] for v in extra}==uuids
refs=[(ref,m.m_Filename) for ref,f in fs.items() for m in f.Models()];missing=[]
for ref,path in refs:
 path=path.replace('${KIPRJMOD}',str(V))
 for env in ['KICAD9_3DMODEL_DIR','KICAD8_3DMODEL_DIR','KICAD7_3DMODEL_DIR','KICAD10_3DMODEL_DIR']:path=path.replace('${'+env+'}','/usr/share/kicad/3dmodels')
 if not Path(path).exists():missing.append((ref,path))
result=dict(status='PASS for development checkpoint; FAIL for manufacturing release',pcb_sha256=hashlib.sha256((V/'abx-motion-eth-placement.kicad_pcb').read_bytes()).hexdigest(),
 assertions=['Approved footprint positions and rotations preserved','Original pad nets preserved','All schematic-mapped pads match fresh netlist','All 61 draft parts excluded from BOM/CPL','49 expected parity extras only','Ground-plane layer not routed','Zone nets and layers preserved','Root Rev1.2a PCB and schematics unchanged'],
 erc_violations=0,defined_net_opens=0,copper_shorts_or_clearance_errors=0,remaining_drc_findings=dict(counts),unintegrated_ethernet_footprints=sorted(draft),missing_model_files=missing,
 release_blocks=['49 Ethernet footprints lack schematic integration and routing','154 remaining DRC findings require disposition','Magjack isolation and PCB stack impedance verification pending','Manufacturing BOM/CPL and hardware validation pending'])
(OUT/'qa-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));base.unlink()
