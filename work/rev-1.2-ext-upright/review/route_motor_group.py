from pathlib import Path
import pcbnew,ast,math,heapq,json
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
T=ast.parse((R/'finish_final_6.py').read_text());exec(compile(ast.Module(body=[q for q in T.body if isinstance(q,(ast.FunctionDef,ast.ClassDef)) and q.name!='main'],type_ignores=[]),'router_definitions','exec'),globals())
b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()};nets={q.GetNetname() for q in fps['J503'].Pads()};tracks=list(b.GetTracks());removed=[]
for t in tracks:
 if t.GetNetname() in nets:removed.append(t.m_Uuid.AsString());b.Remove(t)
router=FastBoundedRouter(b);router.pads=[q for q in router.pads if q[4]>=90 and q[2]<=137 and q[5]>=115 and q[3]<=152];router.segs=[q for q in router.segs if q[9]>=90 and q[7]<=137 and q[10]>=115 and q[8]<=152];router.vias=[q for q in router.vias if 89<q[1]<138 and 114<q[2]<153];base=router.seg_clear;router.seg_clear=lambda net,lid,x1,y1,x2,y2,half_w=.1,clr=.2:base(net,lid,x1,y1,x2,y2,half_w,clr);router.via_clear=lambda *args,**kwargs:False
results=[]
for suffix,preferred in [('A2',0),('A1',1),('B1',0),('B2',1)]:
 net=next(n for n in nets if n.endswith('STEP2_'+suffix));a=next(q.GetPosition() for q in fps['U502'].Pads() if q.GetNetname()==net);z=next(q.GetPosition() for q in fps['J503'].Pads() if q.GetNetname()==net)
 ok=False
 for lid in [preferred,1-preferred]:
  print('A* motor group',net,'layer',lid,flush=True);ok=router.route_astar(net,pcbnew.ToMM(a.x),pcbnew.ToMM(a.y),lid,pcbnew.ToMM(z.x),pcbnew.ToMM(z.y),lid,bbox=(90,115,137,151.7),allow_in2=False,width=.5)
  if ok:break
 results.append({'net':net,'layer':lid,'width_mm':.5,'success':ok})
 assert ok,'Group reroute failed; board not saved: '+net
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'motor-group-routing.json').write_text(json.dumps({'removed_route_ids':removed,'routes':results},indent=2));print('All four motor nets routed automatically.',flush=True)
