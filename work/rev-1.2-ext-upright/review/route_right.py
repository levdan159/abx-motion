"""Route only candidate relay links using isolated legacy geometry/router definitions."""
from pathlib import Path
import pcbnew,json,math,heapq,ast,re
O=Path(__file__).resolve().parent;R=O.parents[2];P=R
# Extract definitions only. No legacy main, globals, checkpoint restore or export code executes.
tree=ast.parse((R/'finish_final_6.py').read_text());defs=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name!='main'];exec(compile(ast.Module(body=defs,type_ignores=[]),'isolated_router_definitions','exec'),globals())
b=pcbnew.LoadBoard(str(P/'abx-motion.kicad_pcb'));j=json.loads((O/'placement-drc.json').read_text());assert not any(v['severity']=='error' for v in j['violations'])
router=FastBoundedRouter(b)
# Spatially restrict obstacle lists, without removing physical objects from the board.
router.pads=[q for q in router.pads if q[4]>=90 and q[2]<=137 and q[5]>=115 and q[3]<=152]
router.segs=[q for q in router.segs if q[9]>=90 and q[7]<=137 and q[10]>=115 and q[8]<=152]
router.vias=[q for q in router.vias if 89<q[1]<138 and 114<q[2]<153]
baseclear=router.seg_clear;router.seg_clear=lambda net,lid,x1,y1,x2,y2,half_w=.10,clr=.20:baseclear(net,lid,x1,y1,x2,y2,half_w,clr)
basevia=router.via_clear;router.via_clear=lambda net,x,y,via_r=.325,clr=.20:False if contact_mode else basevia(net,x,y,via_r,clr)
def addvia(net,x,y,size=.65,drill=.30):
 v=pcbnew.PCB_VIA(b);v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)));v.SetWidth(pcbnew.FromMM(size));v.SetDrill(pcbnew.FromMM(drill));v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);v.SetNet(b.FindNet(net));v.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED);v.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED);b.Add(v);router.vias.append((net,x,y,size/2))
router.add_via=addvia
objects={t.m_Uuid.AsString():t for t in b.GetTracks()}
for f in b.GetFootprints():
 for q in f.Pads():objects[q.m_Uuid.AsString()]=q
def endpoint(item,other):
 o=objects[item['uuid']]
 if isinstance(o,pcbnew.PCB_TRACK) and not isinstance(o,pcbnew.PCB_VIA):
  pts=[o.GetStart(),o.GetEnd()];pos=min(pts,key=lambda v:(pcbnew.ToMM(v.x)-other[0])**2+(pcbnew.ToMM(v.y)-other[1])**2);lid=1 if o.GetLayer()==pcbnew.B_Cu else 0
 else:pos=o.GetPosition();lid=0
 return pcbnew.ToMM(pos.x),pcbnew.ToMM(pos.y),lid
# Back copper artwork is a physical copper obstacle, though it has no net.
for f in b.GetFootprints():
 if f.GetReference()!='LOGO2':continue
 boxes=[g.GetBoundingBox() for g in f.GraphicalItems() if g.GetLayer()==pcbnew.B_Cu]
 if boxes:
  router.pads.append(('__COPPER_ARTWORK__',2,min(pcbnew.ToMM(q.GetLeft()) for q in boxes),min(pcbnew.ToMM(q.GetTop()) for q in boxes),max(pcbnew.ToMM(q.GetRight()) for q in boxes),max(pcbnew.ToMM(q.GetBottom()) for q in boxes),False))
routes=[];links=list(j['unconnected_items'])
motor_nets=set(json.loads((O/'changes.json').read_text())['motor_nets'])
def contact(v):return objects[v['items'][0]['uuid']].GetNetname() in motor_nets
links.sort(key=lambda v:(not contact(v),-math.hypot(v['items'][0]['pos']['x']-v['items'][1]['pos']['x'],v['items'][0]['pos']['y']-v['items'][1]['pos']['y'])))
for link in links:
 i1,i2=link['items'];net=objects[i1['uuid']].GetNetname();target=(i2['pos']['x'],i2['pos']['y']);a=endpoint(i1,target);z=endpoint(i2,a);a=endpoint(i1,z);contact_mode=contact(link);width=.5 if contact_mode else (.4 if net in ['+5V','GND'] else .25)
 bbox=(min(90,a[0]-2,z[0]-2),min(115,a[1]-2,z[1]-2),max(137,a[0]+1,z[0]+1),151.7)
 ok=False
 preferred=0 if net.endswith(('A2','B1')) else 1
 for side in ([preferred,1-preferred] if contact_mode else [None]):
  aa=(*a[:2],side) if side is not None else a;zz=(*z[:2],side) if side is not None else z
  print('Routing',net,aa,zz,'width',width,flush=True)
  ok=router.route_astar(net,*aa,*zz,bbox=bbox,allow_in2=False,width=width)
  if ok:break
 routes.append(dict(net=net,start=a,end=z,width=width,success=ok));pcbnew.SaveBoard(str(P/'abx-motion.kicad_pcb'),b)
 if not ok:print('FAILED',net,flush=True)
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(P/'abx-motion.kicad_pcb'),b)
(O/'routing.json').write_text(json.dumps(routes,indent=2)+'\n');print('Done',sum(r['success'] for r in routes),'of',len(routes),flush=True)
