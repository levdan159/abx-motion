from pathlib import Path
import pcbnew,json,ast,math,heapq,itertools
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
T=ast.parse((R/'finish_final_6.py').read_text());exec(compile(ast.Module(body=[n for n in T.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name!='main'],type_ignores=[]),'router_geometry','exec'),globals())
b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
contactnets={q.GetNetname() for ref in ['J505','J506'] for q in fps[ref].Pads()};tracks=list(b.GetTracks());removed=[]
for t in tracks:
 if t.GetNetname() in contactnets:removed.append(t.m_Uuid.AsString());b.Remove(t)
router=FastBoundedRouter(b)
router.pads=[q for q in router.pads if q[4]>=134 and q[2]<=201 and q[5]>=120 and q[3]<=152]
router.segs=[q for q in router.segs if q[9]>=134 and q[7]<=201 and q[10]>=120 and q[8]<=152]
router.vias=[q for q in router.vias if 133<q[1]<202 and 119<q[2]<153]
for f in b.GetFootprints():
 if f.GetReference()=='LOGO2':
  boxes=[g.GetBoundingBox() for g in f.GraphicalItems() if g.GetLayer()==pcbnew.B_Cu]
  router.pads.append(('__COPPER_ARTWORK__',2,min(pcbnew.ToMM(q.GetLeft()) for q in boxes),min(pcbnew.ToMM(q.GetTop()) for q in boxes),max(pcbnew.ToMM(q.GetRight()) for q in boxes),max(pcbnew.ToMM(q.GetBottom()) for q in boxes),False))
def point(q):v=q.GetPosition();return pcbnew.ToMM(v.x),pcbnew.ToMM(v.y)
def octile(a,z):
 dx,dy=z[0]-a[0],z[1]-a[1];d=min(abs(dx),abs(dy));sx=1 if dx>=0 else -1;sy=1 if dy>=0 else -1
 return [[a,(a[0]+sx*d,a[1]+sy*d),z],[a,(z[0]-sx*d,z[1]-sy*d),z]]
manual={
'RLY1_NO':[(138.5,146.2),(140.3,148),(163,148)],
'RLY1_NC':[(150.5,146.2),(153,143.7),(168.86,143.7),(173.16,148)],
'RLY1_COM':[(144.5,132),(156.5,144),(164.08,144),(168.08,148)],
'RLY2_NO':[(170.7,138.5),(180.2,148),(180.25,148)],
'RLY2_COM':[(156.5,132.5),(169.83,132.5),(185.33,148)],
'RLY2_NC':[(170.7,126.5),(174,123.2),(191.3,123.2),(196,127.9),(196,142.41),(190.41,148)]}
# Put short local circuits first; then assign both outer layers to long contact runs.
order=['RLY1_NO','RLY1_NC','RLY1_COM','RLY2_NO','RLY2_COM','RLY2_NC'];results=[]
for suffix in order:
 net=next(n for n in contactnets if n.endswith(suffix));pads=[q for f in b.GetFootprints() for q in f.Pads() if q.GetNetname()==net];assert len(pads)==2
 a,z=point(pads[0]),point(pads[1]);candidates=octile(a,z)+[manual[suffix],list(reversed(manual[suffix]))]
 for x in range(136,201,2):
  for y in [123.5,125,128,130,133,136,139,141,143,144,145,146,149.8,151]:
   for u in octile(a,(x,y)):
    for w in octile((x,y),z):candidates.append(u+w[1:])
 valid=[]
 for path in candidates:
  if math.dist(path[0],a)>.001 or math.dist(path[-1],z)>.001:continue
  path=[q for k,q in enumerate(path) if k==0 or math.dist(q,path[k-1])>.00001]
  length=sum(math.dist(x,y) for x,y in zip(path,path[1:]))
  for lid in [0,1]:
   if all(router.seg_clear(net,lid,*x,*y,half_w=.4,clr=.20) for x,y in zip(path,path[1:])):valid.append((length+len(path)*.25,lid,path,length))
 assert valid,'No simple contact path for '+net
 _,lid,path,length=min(valid,key=lambda q:q[0]);print(net,'layer',lid,'mm',round(length,2),'nodes',len(path),flush=True)
 for x,y in zip(path,path[1:]):router.add_seg(net,lid,*x,*y,width=.8)
 results.append({'net':net,'layer':b.GetLayerName(router.layer_ids[lid]),'points':path,'length_mm':length,'width_mm':.8})
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(R/'abx-motion.kicad_pcb'),b)
(O/'contact-routing.json').write_text(json.dumps({'removed_grid_track_ids':removed,'routes':results},indent=2))
