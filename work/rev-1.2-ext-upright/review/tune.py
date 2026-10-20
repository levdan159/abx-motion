from pathlib import Path
import pcbnew as p,json
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()};c=json.loads((O/'changes.json').read_text())
for ref,x,y in [('J502',98.1,140.9),('J503',105,148),('J504',119.8,140.9)]:fps[ref].SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)))
remove={'c97e7205-5bd5-4577-9a34-11b48a468740','f264a4a4-6304-48af-9703-d7073e26ba77'};tracks=list(b.GetTracks())
for t in tracks:
 if t.m_Uuid.AsString() in remove:b.Remove(t);c['removed_tracks'].append(t.m_Uuid.AsString())
for t in b.GetDrawings():
 if not isinstance(t,p.PCB_TEXT):continue
 x,y=p.ToMM(t.GetPosition().x),p.ToMM(t.GetPosition().y)
 if t.GetText() in ['J502 EXT1','J504 EXT2']:
  ref=t.GetText().split()[0];cx=p.ToMM(fps[ref].GetPosition().x);t.SetPosition(p.VECTOR2I(p.FromMM(cx-2.6),p.FromMM(144.7)))
 elif t.GetText() in ['EN','STEP','DIR','GND'] and (98.9<x<99.5 or 120.9<x<121.5) and 140<y<149:
  ref='J502' if x<110 else 'J504';n={'EN':'1','STEP':'2','DIR':'3','GND':'4'}[t.GetText()];q=next(q for q in fps[ref].Pads() if q.GetNumber()==n);t.SetPosition(p.VECTOR2I(q.GetPosition().x+p.FromMM(2.8),q.GetPosition().y))
 elif t.GetText()=='J503 STEP2' or t.GetText() in ['A1','A2','B1','B2'] and 103.9<=x<=111.6 and 143<y<146:t.SetPosition(p.VECTOR2I(t.GetPosition().x+p.FromMM(1),t.GetPosition().y))
fps['Q503'].Reference().SetPosition(p.VECTOR2I(p.FromMM(106),p.FromMM(138)))
for q in c['moved']:
 f=fps[q['ref']];q['after']=[p.ToMM(f.GetPosition().x),p.ToMM(f.GetPosition().y),f.GetOrientationDegrees()]
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'changes.json').write_text(json.dumps(c,indent=2))
