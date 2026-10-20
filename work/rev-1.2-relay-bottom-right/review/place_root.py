from pathlib import Path
import pcbnew as p,json,hashlib
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
placements={'K501':(144.5,132,0),'K502':(156.5,131,90),'J505':(163,148,0),'J506':(180.25,148,0),
'R501':(139.5,122.5,0),'R207':(143.5,122.5,0),'Q501':(139.5,126,0),'D501':(145,126.5,0),'R502':(150,125,0),'D502':(150,122,0),
'R503':(153.5,115.8,0),'R208':(157.5,115.8,0),'Q502':(155,118.8,0),'D503':(159,120.5,0),'R504':(168,120.5,0),'D504':(164,120.5,0)}
private={q.GetNetname() for f in b.GetFootprints() for q in f.Pads() if '/Steppers_and_Relays/RLY' in q.GetNetname()}

oldpads=[q for ref in placements for q in fps[ref].Pads() if q.GetNetname() not in private]
legacy=p.LoadBoard(str(R/'work/rev-1.2-relay-bay/review/before.kicad_pcb'));legacyids={t.m_Uuid.AsString() for t in legacy.GetTracks()}
tracks=list(b.GetTracks());removed=[]
for t in tracks:
 remove=t.GetNetname() in private or (t.m_Uuid.AsString() not in legacyids and t.GetNetname() in ['+5V','GND','/RELAY_1','/RELAY_2'])
 if not remove and not isinstance(t,p.PCB_VIA) and t.GetLength()<p.FromMM(8):
  remove=any(q.GetNetname()==t.GetNetname() and p.SHAPE.Collide(q.GetEffectiveShape(t.GetLayer()),t.GetEffectiveShape(t.GetLayer()),0) for q in oldpads)
 if remove:removed.append(t.m_Uuid.AsString());b.Remove(t)
changes=[]
for ref,(x,y,a) in placements.items():
 f=fps[ref];before=[p.ToMM(f.GetPosition().x),p.ToMM(f.GetPosition().y),f.GetOrientationDegrees()]
 f.SetOrientationDegrees(a);f.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)));changes.append({'ref':ref,'before':before,'after':[x,y,a]})
# Remove stale freestanding connector / relay labels by UUID; regenerate at actual pad locations.
uids=['ab0724c3-8426-4964-a544-a67c18579a16','4ac4eeb0-c4a2-40e9-8a34-ce5bcc30253f','ed655804-9f26-441e-9147-377995679431','d003e170-fe10-4709-bba0-589d0c433836','b9b3a275-eecc-4226-b581-dd6fa3933082','5edcd869-f6b0-4015-b838-57b279f5f24e','f6f22e74-b36c-4786-b4e0-0b78b3dd5492','13c007ee-bc06-4d88-a222-c3347c8526ff','04f7d182-835d-4f38-bc19-07e7896e194e','7bd46fa7-c2ff-4f66-abd5-a7752d64444d','cb3d0876-2d2a-4826-8141-17bf29c3ec2f','4a89224e-7e5d-4766-b138-59bd4d9deb2d','669f3003-56bb-4f07-a85b-2efd14ceba81','528924b8-7856-4fdc-ae59-e7d718488cce','ed10f808-3e04-49a4-83a2-8f4ffacb907c']
drawings=list(b.GetDrawings())
for t in drawings:
 if t.m_Uuid.AsString() in uids:b.Remove(t)
def text(s,x,y,layer=p.F_SilkS,size=.8,angle=0):
 t=p.PCB_TEXT(b);t.SetText(s);t.SetLayer(layer);t.SetTextSize(p.VECTOR2I(p.FromMM(size),p.FromMM(size)));t.SetTextThickness(p.FromMM(.12));t.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)));t.SetTextAngle(p.EDA_ANGLE(angle,p.DEGREES_T));t.SetMirrored(layer==p.B_SilkS);b.Add(t)
text('RLY1 ON',150,119.7,size=.8)
text('RLY2 ON',164,118.4,size=.8)
for ref,n in [('J505',1),('J506',2)]:
 f=fps[ref];cx=p.ToMM(f.GetPosition().x)+5.08
 for layer in [p.F_SilkS,p.B_SilkS]:
  for num,s in [('1','NO'),('2','COM'),('3','NC')]:
   q=next(q for q in f.Pads() if q.GetNumber()==num)
   text(s,p.ToMM(q.GetPosition().x),141.1 if layer==p.F_SilkS else 150.7,layer,.75)
  if ref=='J505' and layer==p.F_SilkS:text('J505 RLY1',156.6,146,layer,.8,90)
  else:text(f'{ref} RLY{n}',cx,139.55 if layer==p.F_SilkS else 152.0,layer,.8)
fps['K502'].Reference().SetPosition(p.VECTOR2I(p.FromMM(164),p.FromMM(121.4)))
fps['K502'].Reference().SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T))
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b)
(O/'changes.json').write_text(json.dumps({'moved':changes,'removed_tracks':removed,'private_nets':sorted(private)},indent=2));print('Moved',len(changes),'removed',len(removed))
