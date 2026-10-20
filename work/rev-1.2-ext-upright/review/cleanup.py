from pathlib import Path
import pcbnew as p,json,math,sys
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;report=O/(sys.argv[1] if len(sys.argv)>1 else 'connected-drc.json');j=json.loads(report.read_text());b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));tracks=list(b.GetTracks());pads=[q for f in b.GetFootprints() for q in f.Pads()];byid={t.m_Uuid.AsString():t for t in tracks};removed=set();edits=[]
for v in j['violations']:
 if v['type'] not in ['track_dangling','via_dangling']:continue
 t=byid[v['items'][0]['uuid']];uid=t.m_Uuid.AsString()
 if isinstance(t,p.PCB_VIA) or t.GetLength()<p.FromMM(.05):b.Remove(t);removed.add(uid);edits.append({'uuid':uid,'net':t.GetNetname(),'action':'remove unused via/zero-length segment'});continue
 a,z=t.GetStart(),t.GetEnd();dx,dy=z.x-a.x,z.y-a.y;den=dx*dx+dy*dy;params=[]
 def at(u):return p.VECTOR2I(round(a.x+dx*u),round(a.y+dy*u))
 def project(v):return min(1,max(0,((v.x-a.x)*dx+(v.y-a.y)*dy)/den))
 def accept(item,v):
  u=project(v);q=at(u)
  if item.HitTest(q) and t.HitTest(v):params.append(u)
 for q in pads:
  if q.GetNetname()!=t.GetNetname() or not q.GetLayerSet().Contains(t.GetLayer()):continue
  u=project(q.GetPosition())
  if q.HitTest(at(u)):params.append(u)
  for u in [0,1]:
   if q.HitTest(at(u)):params.append(u)
 for other in tracks:
  if other==t or other.m_Uuid.AsString() in removed or other.GetNetname()!=t.GetNetname():continue
  if isinstance(other,p.PCB_VIA):
   if t.HitTest(other.GetPosition()):params.append(project(other.GetPosition()))
   continue
  if other.GetLayer()!=t.GetLayer():continue
  for q in [other.GetStart(),other.GetEnd()]:accept(other,q)
  for u in [0,1]:
   if other.HitTest(at(u)):params.append(u)
  c,d=other.GetStart(),other.GetEnd();ex,ey=d.x-c.x,d.y-c.y;cross=dx*ey-dy*ex
  if cross:
   u=((c.x-a.x)*ey-(c.y-a.y)*ex)/cross;w=((c.x-a.x)*dy-(c.y-a.y)*dx)/cross
   if 0<=u<=1 and 0<=w<=1:params.append(u)
 if not params or max(params)-min(params)<1e-7:b.Remove(t);removed.add(uid);action='remove free stub'
 else:t.SetStart(at(min(params)));t.SetEnd(at(max(params)));action='trim to connected branch points'
 edits.append({'uuid':uid,'net':t.GetNetname(),'action':action})
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);log=O/'cleanup.json';prev=json.loads(log.read_text()) if log.exists() else [];log.write_text(json.dumps(prev+edits,indent=2));print('Pruned',len(edits),'reported local remnants.')
