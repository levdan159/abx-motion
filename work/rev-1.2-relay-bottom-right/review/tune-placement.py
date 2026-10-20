from pathlib import Path
import pcbnew as p,json
r=Path.cwd();o=r/Path(__file__).resolve().parent.relative_to(r);b=p.LoadBoard(str(r/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
for ref,x,y in [('K502',156.5,132.5),('R503',153.9,115.8)]:fps[ref].SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)))
fps['K502'].Reference().SetPosition(p.VECTOR2I(p.FromMM(166),p.FromMM(122.4)))
for t in b.GetDrawings():
 if isinstance(t,p.PCB_TEXT) and t.GetLayer()==p.F_SilkS and t.GetText() in ['NO','COM','NC'] and 160<p.ToMM(t.GetPosition().x)<192 and 140<p.ToMM(t.GetPosition().y)<142:
  pos=t.GetPosition();pos.y=p.FromMM(141.7);t.SetPosition(pos);t.SetTextSize(p.VECTOR2I(p.FromMM(.65),p.FromMM(.65)))
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(r/'abx-motion.kicad_pcb'),b)
c=json.loads((o/'changes.json').read_text())
for q in c['moved']:
 f=fps[q['ref']];q['after']=[p.ToMM(f.GetPosition().x),p.ToMM(f.GetPosition().y),f.GetOrientationDegrees()]
(o/'changes.json').write_text(json.dumps(c,indent=2))
