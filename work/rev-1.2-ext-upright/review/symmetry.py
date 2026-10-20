from pathlib import Path
import pcbnew as p,json
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()};f=fps['J501'];nets={q.GetNetname() for q in f.Pads()};tracks=list(b.GetTracks());removed=[]
for t in tracks:
 if t.GetNetname() in nets:removed.append(t.m_Uuid.AsString());b.Remove(t)
f.SetPosition(p.VECTOR2I(p.FromMM(96.5),p.FromMM(148)))
for t in b.GetDrawings():
 if not isinstance(t,p.PCB_TEXT):continue
 x,y=p.ToMM(t.GetPosition().x),p.ToMM(t.GetPosition().y)
 if t.GetText()=='J501 STEP1' or t.GetText() in ['A1','A2','B1','B2'] and 95.1<=x<=102.8 and 143<y<146:t.SetPosition(p.VECTOR2I(t.GetPosition().x+p.FromMM(1.3),t.GetPosition().y))
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'symmetry.json').write_text(json.dumps({'ref':'J501','shift_right_mm':1.3,'removed_motor1_route_ids':removed,'jst_to_ext_courtyard_gap_mm':2.53},indent=2));c=json.loads((O/'changes.json').read_text())
for q in c['moved']:
 if q['ref']=='J501':q['after']=[96.5,148,0]
(O/'changes.json').write_text(json.dumps(c,indent=2))
