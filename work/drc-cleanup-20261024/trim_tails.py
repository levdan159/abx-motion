from pathlib import Path
import pcbnew,json,math,sys
from shapely.geometry import LineString,Point
from shapely.ops import nearest_points
R=Path.cwd();O=R/'work/drc-cleanup-20261024';report=json.loads((O/(sys.argv[1] if len(sys.argv)>1 else 'copper-drc.json')).read_text());b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));b.BuildConnectivity();c=b.GetConnectivity();uid=lambda o:o.m_Uuid.AsString();xy=lambda p:(p.x/1e6,p.y/1e6);vec=lambda p:pcbnew.VECTOR2I(round(p[0]*1e6),round(p[1]*1e6));ts={uid(t):t for t in b.GetTracks()};changes=[];holds=[]
def groups():
 co=b.GetConnectivity();ps={uid(p):p for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode()>0};seen=set();out=[]
 for u,p in ps.items():
  if u in seen:continue
  g={u}|{uid(v) for v in co.GetConnectedItems(p) if v.GetClass()=='PAD' and uid(v) in ps};seen|=g;out.append(sorted(g))
 return sorted(out)
before=groups()
for v in report['violations']:
 if v['type']!='track_dangling':continue
 t=ts[v['items'][0]['uuid']];p=pcbnew.VECTOR2I(0,0)
 if not c.TestTrackEndpointDangling(t,False,p):continue
 a,z=xy(t.GetStart()),xy(t.GetEnd());line=LineString([a,z]);start=math.dist(xy(p),a)<1e-5;choices=[]
 for q in list(c.GetConnectedTracks(t)):
  if q.GetClass()=='PCB_TRACK':
   if q.GetLayer()!=t.GetLayer():continue
   shape=LineString([xy(q.GetStart()),xy(q.GetEnd())])
  elif q.GetClass()=='PCB_VIA':shape=Point(xy(q.GetPosition()))
  else:continue
  u,w=nearest_points(line,shape);dist=u.distance(w);fac=line.project(u,normalized=True)
  if (start and fac<1e-5) or (not start and fac>1-1e-5):continue
  choices.append((fac if start else 1-fac,xy(vec((u.x,u.y))), (w.x,w.y),q,dist))
 if not choices:continue
 _,target,qpoint,q,gap=min(choices,key=lambda q:q[0]);old=(a,z)
 if math.dist(target,a if start else z)<.001:continue
 if start:t.SetStart(vec(target))
 else:t.SetEnd(vec(target))
 if gap>1e-6:
  # Bridge the former edge-only contact to an explicit centerline junction.
  bridge=pcbnew.PCB_TRACK(b);bridge.SetStart(vec(target));bridge.SetEnd(vec(qpoint));bridge.SetLayer(t.GetLayer());bridge.SetWidth(t.GetWidth());bridge.SetNetCode(t.GetNetCode());b.Add(bridge);holds.append(bridge)
 changes.append(dict(uuid=uid(t),net=t.GetNetname(),old=old,new=[xy(t.GetStart()),xy(t.GetEnd())],junction_gap_mm=gap))
 b.BuildConnectivity();c=b.GetConnectivity()
# Try the remaining native one-layer vias, checking actual pad connectivity.
for v in report['violations']:
 if v['type']!='via_dangling':continue
 t=ts[v['items'][0]['uuid']];holds.append(t);b.Remove(t);b.BuildConnectivity()
 if groups()!=before:b.Add(t);b.BuildConnectivity()
 else:changes.append(dict(uuid=uid(t),net=t.GetNetname(),reason='one-layer via removed; native pad groups unchanged'))
pcbnew.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();assert groups()==before,'Trim changes pad connectivity'
pcbnew.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'tail-trims.json').write_text(json.dumps(changes,indent=2)+'\n');print('Trimmed/removed',len(changes),'objects; native pad groups unchanged')
