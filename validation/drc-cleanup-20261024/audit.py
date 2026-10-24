from pathlib import Path
import json,collections,subprocess,hashlib,xml.etree.ElementTree as ET
import pcbnew
R=Path.cwd();O=R/'validation/drc-cleanup-20261024';P=O/'baseline.kicad_pcb';P.write_bytes(subprocess.check_output(['git','show','41f87bf:abx-motion.kicad_pcb']));a=pcbnew.LoadBoard(str(P));b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));uid=lambda t:t.m_Uuid.AsString();fs={f.GetReference():f for f in b.GetFootprints()};afs={f.GetReference():f for f in a.GetFootprints()}
assert set(fs)==set(afs)|{'TIM_ESP'}
for ref,f in afs.items():
 g=fs[ref];assert f.GetPosition()==g.GetPosition() and f.GetOrientationDegrees()==g.GetOrientationDegrees(),ref
 def data(f):return {uid(p):(p.GetNumber(),p.GetNetname(),tuple(p.GetPosition()),tuple(p.GetSize()),tuple(p.GetDrillSize()),p.GetShape(),tuple(p.GetLayerSet().Seq())) for p in f.Pads()}
 assert data(f)==data(g),ref
originalpads={uid(p) for f in a.GetFootprints() for p in f.Pads() if p.GetNetCode()>0}
def groups(board):
 board.BuildConnectivity();c=board.GetConnectivity();ps={uid(p):p for f in board.GetFootprints() for p in f.Pads() if uid(p) in originalpads};seen=set();out=[]
 for u,p in ps.items():
  if u in seen:continue
  g={u}|{uid(v) for v in c.GetConnectedItems(p) if v.GetClass()=='PAD' and uid(v) in ps};seen|=g;out.append(sorted(g))
 return sorted(out)
assert groups(a)==groups(b),'Original connected pad partitions changed'
def zs(board):return {uid(z):(z.GetNetname(),tuple(z.GetLayerSet().Seq()),z.GetAssignedPriority(),tuple(z.GetBoundingBox().GetPosition()),tuple(z.GetBoundingBox().GetSize())) for z in board.Zones()}
assert zs(a)==zs(b),'Original zones changed'
groundvias={uid(t) for t in a.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND'};assert groundvias<={uid(t) for t in b.GetTracks()}
expected={}
for net in ET.parse(O/'netlist.xml').findall('.//nets/net'):
 for n in net.findall('node'):expected[(n.get('ref'),n.get('pin'))]=net.get('name')
for ref,f in fs.items():
 for p in f.Pads():
  if (ref,p.GetNumber()) in expected:assert p.GetNetname()==expected[(ref,p.GetNumber())],(ref,p.GetNumber())
reserved=json.load(open(R/'work/drc-cleanup-20261024/board-only-reserves.json'));assert len(reserved)==49
for ref in reserved:
 f=fs[ref];assert f.GetAttributes()&pcbnew.FP_BOARD_ONLY;assert all(p.GetNetCode()==0 for p in f.Pads());assert f.IsExcludedFromBOM() and f.IsExcludedFromPosFiles()
tim=fs['TIM_ESP'];pads=list(tim.Pads());assert len(pads)==1;pad=pads[0];assert pad.GetNetname()=='GND' and pad.GetSize()==pcbnew.VECTOR2I(4000000,4000000) and pad.GetPosition()==pcbnew.VECTOR2I(99500000,62460000);assert not pad.IsOnLayer(pcbnew.B_Paste)
assert (R/'abx-motion.kicad_pro').read_bytes()==subprocess.check_output(['git','show','41f87bf:abx-motion.kicad_pro']),'Rules/settings changed'
drc=json.load(open(O/'final-drc.json'));assert not drc['violations'] and not drc['schematic_parity'] and not drc['unconnected_items']
erc=json.load(open(O/'final-erc.json'));assert not any(s.get('violations') for s in erc.get('sheets',[]))
result=dict(status='Clean DRC/ERC for the currently integrated draft',baseline='41f87bf',drc_violations=0,schematic_parity_issues=0,defined_net_opens=0,erc_violations=0,no_rules_relaxed_or_exclusions_added=True,original_pad_nets_geometry_and_connected_groups_preserved=True,all_component_positions_preserved=True,all_original_ground_vias_and_zone_boundaries_preserved=True,thermal_pad=dict(net='GND',mask_mm=[4,4],paste=False),unintegrated_board_only_ethernet_reserves=49,manufacturing_ready=False,pcb_sha256=hashlib.sha256((R/'abx-motion.kicad_pcb').read_bytes()).hexdigest())
(O/'qa-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));P.unlink()
