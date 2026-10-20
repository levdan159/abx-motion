from pathlib import Path
import pcbnew,json,ast,math,heapq
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
T=ast.parse((R/'finish_final_6.py').read_text());exec(compile(ast.Module(body=[x for x in T.body if isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name!='main'],type_ignores=[]),'router_definitions','exec'),globals())
b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));tracks=list(b.GetTracks());byid={t.m_Uuid.AsString():t for t in tracks};router=FastBoundedRouter(b);router.pads=[q for q in router.pads if q[4]>=90 and q[2]<=137 and q[5]>=130 and q[3]<=152];router.segs=[q for q in router.segs if q[9]>=90 and q[7]<=137 and q[10]>=130 and q[8]<=152];router.vias=[q for q in router.vias if 89<q[1]<138 and 129<q[2]<153];base=router.seg_clear;router.seg_clear=lambda net,lid,x1,y1,x2,y2,half_w=.1,clr=.2:base(net,lid,x1,y1,x2,y2,half_w,clr)
j=json.loads((O/'motor-routed-drc.json').read_text());link=next(x for x in j['unconnected_items'] if 'BTN_BACK' in x['items'][0]['description']);ta,tz=[byid[x['uuid']] for x in link['items']];net=ta.GetNetname()
def clear_endpoint(t,target):
 ends=[t.GetStart(),t.GetEnd()];near=min(ends,key=lambda v:math.hypot(pcbnew.ToMM(v.x)-target[0],pcbnew.ToMM(v.y)-target[1]));far=ends[1] if near==ends[0] else ends[0];ax,ay,zx,zy=map(pcbnew.ToMM,[near.x,near.y,far.x,far.y]);n=max(1,int(math.hypot(zx-ax,zy-ay)/.1));lid=1 if t.GetLayer()==pcbnew.B_Cu else 0
 for k in range(n+1):
  x,y=ax+(zx-ax)*k/n,ay+(zy-ay)*k/n
  gx,gy=round(round(x/.2)*.2,3),round(round(y/.2)*.2,3)
  if router.seg_clear(net,lid,x,y,gx,gy,half_w=.125,clr=.20) and router.seg_clear(net,lid,gx,gy,gx,gy,half_w=.125,clr=.20):
   if near==ends[0]:t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)))
   else:t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)))
   return x,y,lid
 raise RuntimeError('No clear attachment point')
a=clear_endpoint(ta,tuple(pcbnew.ToMM(v) for v in [tz.GetPosition().x,tz.GetPosition().y]));z=clear_endpoint(tz,a);print('Automatic legal attachment points',a,z,flush=True)
assert router.route_astar(net,*a,*z,bbox=(90,130,137,151.7),allow_in2=False,width=.25)
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'button-routing.json').write_text(json.dumps({'net':net,'source':a,'target':z,'trimmed_tracks':[ta.m_Uuid.AsString(),tz.m_Uuid.AsString()]},indent=2))
