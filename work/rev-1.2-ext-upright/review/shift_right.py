from pathlib import Path
import pcbnew as p,json
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
refs=['J501','J502','J503','J504','R507'];oldpads=[q for ref in refs for q in fps[ref].Pads()];motornets={q.GetNetname() for ref in ['J501','J503'] for q in fps[ref].Pads()};c=json.loads((O/'changes.json').read_text());tracks=list(b.GetTracks());removed=[]
for t in tracks:
 remove=t.GetNetname() in motornets
 if not remove and not isinstance(t,p.PCB_VIA):remove=any(q.GetNetname()==t.GetNetname() and min((t.GetStart()-q.GetPosition()).EuclideanNorm(),(t.GetEnd()-q.GetPosition()).EuclideanNorm())<p.FromMM(1.2) for q in oldpads)
 if remove:b.Remove(t);removed.append(t.m_Uuid.AsString())
oldpositions={ref:(p.ToMM(fps[ref].GetPosition().x),p.ToMM(fps[ref].GetPosition().y)) for ref in refs}
for ref,x,y in [('J501',95.2,148),('J502',111.3,140.9),('J503',118.2,148),('J504',133,140.9),('R507',110.2,137)]:fps[ref].SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)))
# Move the existing motor connector legends with the exact footprint displacement.
for t in b.GetDrawings():
 if not isinstance(t,p.PCB_TEXT):continue
 x,y=p.ToMM(t.GetPosition().x),p.ToMM(t.GetPosition().y)
 if t.GetText() in ['J501 STEP1','J503 STEP2']:
  ref=t.GetText().split()[0];dx=p.ToMM(fps[ref].GetPosition().x)-oldpositions[ref][0];t.SetPosition(p.VECTOR2I(t.GetPosition().x+p.FromMM(dx),t.GetPosition().y));continue
 if t.GetText() in ['A1','A2','B1','B2'] and 143<y<146:
  ref='J501' if 81.9<=x<=89.6 else ('J503' if 104.9<=x<=112.6 else None)
  if ref:
   dx=p.ToMM(fps[ref].GetPosition().x)-oldpositions[ref][0];t.SetPosition(p.VECTOR2I(t.GetPosition().x+p.FromMM(dx),t.GetPosition().y));continue
 if t.GetText() in ['J502 EXT1','J504 EXT2']:
  ref=t.GetText().split()[0];cx=p.ToMM(fps[ref].GetPosition().x);t.SetPosition(p.VECTOR2I(p.FromMM(cx-2.6),p.FromMM(144.7)));continue
 if t.GetText() in ['EN','STEP','DIR','GND'] and (100.6<x<101.3 or 122.1<x<123.1) and 140<y<150:
  ref='J502' if x<110 else 'J504';n={'EN':'1','STEP':'2','DIR':'3','GND':'4'}[t.GetText()];q=next(q for q in fps[ref].Pads() if q.GetNumber()==n)
  offset=2.8 if ref=='J502' else 2.4;t.SetPosition(p.VECTOR2I(q.GetPosition().x+p.FromMM(offset),q.GetPosition().y));t.SetTextAngle(p.EDA_ANGLE(0 if ref=='J502' else 90,p.DEGREES_T));t.SetTextSize(p.VECTOR2I(p.FromMM(.6),p.FromMM(.6)))
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b)
# Consolidate final positions against the saved starting board.
base=p.LoadBoard(str(O/'before.kicad_pcb'));original={f.GetReference():f for f in base.GetFootprints()};c['moved']=[]
for ref in refs:
 f=original[ref];g=fps[ref];c['moved'].append({'ref':ref,'before':[p.ToMM(f.GetPosition().x),p.ToMM(f.GetPosition().y),f.GetOrientationDegrees()],'after':[p.ToMM(g.GetPosition().x),p.ToMM(g.GetPosition().y),g.GetOrientationDegrees()]})
c['removed_tracks']+=removed;c['motor_nets']=sorted(motornets);(O/'changes.json').write_text(json.dumps(c,indent=2));print('Whole bank shifted 13.2mm right; J501 now95.2, J503118.2; EXT111.3/133.0.')
