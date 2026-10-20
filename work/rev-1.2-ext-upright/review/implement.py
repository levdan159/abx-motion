from pathlib import Path
import pcbnew as p,sexpdata as sx,json,re,csv
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
name='EXT_Header_1x04_P2.54mm_Vertical';lib=R/'abx-footprints.pretty';src=Path('/usr/share/kicad/footprints/Connector_PinHeader_2.54mm.pretty/PinHeader_1x04_P2.54mm_Vertical.kicad_mod');tree=sx.loads(src.read_text());tree[1]=name
tag=lambda x:str(x[0]) if isinstance(x,list) and x else ''
for x in tree:
 if tag(x)=='pad':next(q for q in x if tag(q)=='drill')[1]=1.1
(lib/(name+'.kicad_mod')).write_text(sx.dumps(tree)+'\n')
b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()};refs=['J502','J503','J504'];oldfps=[fps[k] for k in refs]
private={q.GetNetname() for q in fps['J503'].Pads()};oldpads=[q for ref in ['J502','J504'] for q in fps[ref].Pads()];tracks=list(b.GetTracks());removed=[]
for t in tracks:
 remove=t.GetNetname() in private
 if not remove and not isinstance(t,p.PCB_VIA):
  remove=any(q.GetNetname()==t.GetNetname() and (t.GetStart()-q.GetPosition()).EuclideanNorm()<p.FromMM(1.2) or q.GetNetname()==t.GetNetname() and (t.GetEnd()-q.GetPosition()).EuclideanNorm()<p.FromMM(1.2) for q in oldpads)
 if remove:removed.append(t.m_Uuid.AsString());b.Remove(t)
changes=[]
for ref,x in [('J502',96.8),('J504',118.8)]:
 old=fps[ref];oldpos=[p.ToMM(old.GetPosition().x),p.ToMM(old.GetPosition().y),old.GetOrientationDegrees()];nets={q.GetNumber():q.GetNet() for q in old.Pads()}
 f=p.FootprintLoad(str(lib),name);f.SetParent(b);f.SetReference(ref);f.SetValue(old.GetValue());f.SetPath(old.GetPath());f.SetUuid(old.m_Uuid);f.SetFPID(p.LIB_ID('abx-footprints',name));f.SetOrientationDegrees(0);f.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(140.3)))
 for q in f.Pads():q.SetNet(nets[q.GetNumber()])
 for n,value in [('Datasheet','https://www.we-online.com/components/products/datasheet/61300411121.pdf'),('Manufacturer','Wurth Elektronik'),('MPN','61300411121')]:
  f.SetField(n,value);f.GetField(n).SetVisible(False);f.GetField(n).SetLayer(p.F_Fab)
 f.Reference().SetVisible(False);f.Value().SetVisible(False);b.Remove(old);b.Add(f);fps[ref]=f;changes.append({'ref':ref,'before':oldpos,'after':[x,140.3,0]})
f=fps['J503'];oldpos=[p.ToMM(f.GetPosition().x),p.ToMM(f.GetPosition().y),f.GetOrientationDegrees()];f.SetPosition(p.VECTOR2I(p.FromMM(104),p.FromMM(148)));changes.append({'ref':'J503','before':oldpos,'after':[104,148,0]})
# Reuse existing drawing UUIDs for both front/rear control legends.
for t in b.GetDrawings():
 if not isinstance(t,p.PCB_TEXT):continue
 x,y=p.ToMM(t.GetPosition().x),p.ToMM(t.GetPosition().y)
 if t.GetText() in ['J502 EXT1','J504 EXT2']:
  ref=t.GetText().split()[0];cx=96.8 if ref=='J502' else 118.8;t.SetPosition(p.VECTOR2I(p.FromMM(cx-2.6),p.FromMM(144.4)));t.SetTextAngle(p.EDA_ANGLE(90,p.DEGREES_T));t.SetTextSize(p.VECTOR2I(p.FromMM(.65),p.FromMM(.65)));continue
 if t.GetText() in ['EN','STEP','DIR','GND'] and abs(y-145.5)<.001 and (95.9<=x<=103.7 or 123.9<=x<=131.7):
  ref='J502' if x<110 else 'J504';padnum={'EN':'1','STEP':'2','DIR':'3','GND':'4'}[t.GetText()];q=next(q for q in fps[ref].Pads() if q.GetNumber()==padnum)
  t.SetPosition(p.VECTOR2I(q.GetPosition().x+p.FromMM(2.4),q.GetPosition().y));t.SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T));t.SetMirrored(t.GetLayer()==p.B_SilkS);continue
 if (t.GetText()=='J503 STEP2' or t.GetText() in ['A1','A2','B1','B2'] and 109.9<=x<=117.6 and 143<y<146):t.SetPosition(p.VECTOR2I(t.GetPosition().x-p.FromMM(6),t.GetPosition().y))
# Exact metadata substitutions affect J502/J504 only, including current procurement overrides.
sch=R/'Steppers_Relays.kicad_sch';s=sch.read_text();s=s.replace('abx-footprints:EXT_Header_1x04_P2.54mm_RightAngle','abx-footprints:'+name).replace('61300411021','61300411121');sch.write_text(s)
pth=R/'design/rev-1.2-parts-overrides.csv';s=pth.read_text().replace('61300411021','61300411121').replace('EXT_Header_1x04_P2.54mm_RightAngle',name);pth.write_text(s)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'changes.json').write_text(json.dumps({'moved':changes,'removed_tracks':removed,'motor_nets':sorted(private)},indent=2));print('Upright headers and compacted J503; removed',len(removed),'local track objects.')
