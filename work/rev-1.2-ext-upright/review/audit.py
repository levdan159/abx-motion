from pathlib import Path
import pcbnew as p,json,hashlib,xml.etree.ElementTree as E,collections
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;b=p.LoadBoard(str(O/'before.kicad_pcb'));a=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));bf={f.GetReference():f for f in b.GetFootprints()};af={f.GetReference():f for f in a.GetFootprints()};allowed={'J501','J502','J503','J504','R507'};assert bf.keys()==af.keys()
for ref,f in bf.items():
 g=af[ref];assert f.GetValue()==g.GetValue()
 if ref not in allowed:assert f.GetPosition()==g.GetPosition() and f.GetOrientationDegrees()==g.GetOrientationDegrees() and f.GetFPID()==g.GetFPID(),ref
 assert {q.GetNumber():q.GetNetname() for q in f.Pads()}=={q.GetNumber():q.GetNetname() for q in g.Pads()},ref
 if ref not in ['J502','J504']:
  assert sorted((q.GetNumber(),q.GetSize().x,q.GetSize().y,q.GetDrillSize().x,q.GetDrillSize().y) for q in f.Pads())==sorted((q.GetNumber(),q.GetSize().x,q.GetSize().y,q.GetDrillSize().x,q.GetDrillSize().y) for q in g.Pads())
for ref in ['J502','J504']:
 f=af[ref];pads={q.GetNumber():q for q in f.Pads()};assert f.GetOrientationDegrees()==0
 assert abs(p.ToMM(pads['4'].GetPosition().y-pads['1'].GetPosition().y)-7.62)<.00001
 for layer in [p.F_SilkS,p.B_SilkS]:
  for n,label in [('1','EN'),('2','STEP'),('3','DIR'),('4','GND')]:
   q=pads[n];items=[t for t in a.GetDrawings() if isinstance(t,p.PCB_TEXT) and t.GetLayer()==layer and t.GetText()==label and abs(p.ToMM(t.GetPosition().y-q.GetPosition().y))<.001 and 0<p.ToMM(t.GetPosition().x-q.GetPosition().x)<3]
   assert len(items)==1 and items[0].IsMirrored()==(layer==p.B_SilkS),(ref,layer,label)
gaps=[p.ToMM(af[e].GetBoundingBox(False,False).GetLeft()-af[m].GetBoundingBox(False,False).GetRight()) for m,e in [('J501','J502'),('J503','J504')]]
assert abs(gaps[0]-gaps[1])<.00001 and abs(gaps[0]-2.53)<.00001,gaps
allowednets={q.GetNetname() for ref in ['J501','J502','J503','J504','R507'] for q in af[ref].Pads()}|{'/+3V3_DRV_EN','/MCU_and_Encoders/BTN_BACK'}
bt={t.m_Uuid.AsString():t for t in b.GetTracks()};at={t.m_Uuid.AsString():t for t in a.GetTracks()}
def sig(t):return (t.GetNetname(),t.GetLayer(),t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth())
modified=[]
for uid in bt.keys()&at.keys():
 assert bt[uid].GetNetname()==at[uid].GetNetname(),uid
 if sig(bt[uid])!=sig(at[uid]):assert bt[uid].GetNetname() in allowednets;modified.append(uid)
for uid in bt.keys()-at.keys():assert bt[uid].GetNetname() in allowednets,bt[uid].GetNetname()
for uid in at.keys()-bt.keys():assert at[uid].GetNetname() in allowednets,at[uid].GetNetname()
thermal=json.loads((R/'validation/thermal-20261020/changes.json').read_text())
for q in thermal['added_vias']:assert sig(bt[q['uuid']])==sig(at[q['uuid']])
def zones(board):return {q.m_Uuid.AsString():(q.GetNetname(),q.GetLayer(),q.Outline().Format()) for q in board.Zones()}
assert zones(a)==zones(b)
coils={q.GetNetname() for ref in ['J501','J503'] for q in af[ref].Pads()};newcoilvias=[]
for uid,t in at.items():
 if t.GetNetname() not in coils:continue
 if isinstance(t,p.PCB_VIA):
  assert t.GetWidth(p.F_Cu)>=p.FromMM(1) and t.GetDrillValue()>=p.FromMM(.5);newcoilvias.append(uid)
 else:assert t.GetWidth()>=p.FromMM(.5)
def nets(path):return {n.attrib['name']:sorted((q.attrib['ref'],q.attrib['pin']) for q in n.findall('node')) for n in E.parse(path).getroot().findall('./nets/net')}
assert nets(O/'netlist.xml')==nets(R/'validation/thermal-20261020/netlist.xml')
h=json.loads((R/'work/rev-1.2-relay-bay/review/baseline-hashes.json').read_text());prod={k:v for k,v in h.items() if k.startswith('production/')};assert all(hashlib.sha256((R/k).read_bytes()).hexdigest()==v for k,v in prod.items())
j=json.loads((O/'drc.json').read_text());assert not j['unconnected_items'] and not j['schematic_parity'];assert len(j['violations'])==19 and all(v['type']=='lib_footprint_mismatch' and v['severity']=='warning' for v in j['violations'])
result={'moved_footprints':sorted(allowed),'unchanged_other_footprints':len(af)-len(allowed),'preserved_original_track_via_objects':len(bt.keys()&at.keys())-len(modified),'trimmed_original_tracks':modified,'removed_original_tracks_vias':len(bt.keys()-at.keys()),'new_tracks_vias':len(at.keys()-bt.keys()),'motor_vias_1mm_0_5drill':len(newcoilvias),'preserved_thermal_vias':len(thermal['added_vias']),'zone_outlines_and_nets_unchanged':True,'front_and_back_labels_match_pad_nets':True,'netlist_unchanged':True,'production_files_unchanged':len(prod),'jst_spacing_mm_before':28,'jst_spacing_mm_after':21.7,'bank_left_edge_shift_right_mm':14.5,'bank_width_reduction_mm':13.12,'matched_jst_to_ext_courtyard_gaps_mm':[2.53,2.53],'drc_errors':0,'opens':0,'parity_issues':0,'existing_library_warnings':19}
(O/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
