from pathlib import Path
import pcbnew as p,json,collections
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));old=p.LoadBoard(str(O/'before.kicad_pcb'));oldids={t.m_Uuid.AsString() for t in old.GetTracks()}
tracks=list(b.GetTracks());dangling={i['uuid'] for v in json.loads((O/'routed-drc.json').read_text())['violations'] if v['type']=='via_dangling' for i in v['items']}
removed=[]
for t in tracks:
 if t.m_Uuid.AsString() in dangling:b.Remove(t);removed.append(t.m_Uuid.AsString())
# Coalesce collinear new-route segments only. Preserve pad/via connection nodes and branches.
anchors=set()
for f in b.GetFootprints():
 for q in f.Pads():
  v=q.GetPosition()
  for layer in [p.F_Cu,p.B_Cu]:
   if q.GetLayerSet().Contains(layer):anchors.add((q.GetNetname(),layer,v.x,v.y))
for t in tracks:
 if isinstance(t,p.PCB_VIA) and t.m_Uuid.AsString() not in removed:
  v=t.GetPosition()
  for layer in [p.F_Cu,p.B_Cu]:anchors.add((t.GetNetname(),layer,v.x,v.y))
active={t.m_Uuid.AsString():t for t in tracks if not isinstance(t,p.PCB_VIA) and t.m_Uuid.AsString() not in oldids}
merged=[]
while True:
 nodes=collections.defaultdict(list)
 for uid,t in active.items():
  for v in [t.GetStart(),t.GetEnd()]:nodes[(t.GetNetname(),t.GetLayer(),v.x,v.y)].append(uid)
 changed=False
 for key,uids in nodes.items():
  if len(uids)!=2 or key in anchors:continue
  a,z=[active[u] for u in uids]
  if a.GetWidth()!=z.GetWidth():continue
  _,_,x,y=key
  av=a.GetEnd() if a.GetStart().x==x and a.GetStart().y==y else a.GetStart()
  zv=z.GetEnd() if z.GetStart().x==x and z.GetStart().y==y else z.GetStart()
  dx,dy=av.x-x,av.y-y;ex,ey=zv.x-x,zv.y-y
  if dx*ey-dy*ex!=0 or dx*ex+dy*ey>=0:continue
  a.SetStart(av);a.SetEnd(zv);b.Remove(z);del active[uids[1]];merged.append(uids[1]);changed=True;break
 if not changed:break
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b)
(O/'polish.json').write_text(json.dumps({'removed_unused_vias':removed,'merged_collinear_new_segments':len(merged)},indent=2));print('Removed',len(removed),'unused vias; merged',len(merged),'collinear segments.')
