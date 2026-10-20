from pathlib import Path
import pcbnew,ast,math,heapq,json
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
T=ast.parse((R/'finish_final_6.py').read_text());exec(compile(ast.Module(body=[q for q in T.body if isinstance(q,(ast.FunctionDef,ast.ClassDef)) and q.name!='main'],type_ignores=[]),'router_definitions','exec'),globals())
b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()};nets={q.GetNetname() for ref in ['J501','J503'] for q in fps[ref].Pads()};tracks=list(b.GetTracks());removed=[]
for t in tracks:
 if t.GetNetname() in nets:removed.append(t.m_Uuid.AsString());b.Remove(t)
router=FastBoundedRouter(b);router.pads=[q for q in router.pads if q[4]>=90 and q[2]<=137 and q[5]>=115 and q[3]<=152];router.segs=[q for q in router.segs if q[9]>=90 and q[7]<=137 and q[10]>=115 and q[8]<=152];router.vias=[q for q in router.vias if 89<q[1]<138 and 114<q[2]<153];base=router.seg_clear;router.seg_clear=lambda net,lid,x1,y1,x2,y2,half_w=.1,clr=.2:base(net,lid,x1,y1,x2,y2,half_w,clr);basevia=router.via_clear
router.via_clear=lambda net,x,y,via_r=.5,clr=.2:basevia(net,x,y,.5,.2)
def addvia(net,x,y,size=1.0,drill=.5):
 v=pcbnew.PCB_VIA(b);v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)));v.SetWidth(pcbnew.FromMM(size));v.SetDrill(pcbnew.FromMM(drill));v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);v.SetNet(b.FindNet(net));v.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED);v.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED);b.Add(v);router.vias.append((net,x,y,size/2))
router.add_via=addvia
results=[]
for ch,suffix,preferred in [(2,'A2',0),(1,'A2',0),(2,'A1',1),(1,'A1',1),(2,'B1',0),(1,'B1',0),(2,'B2',1),(1,'B2',1)]:
 net=next(n for n in nets if n.endswith(f'STEP{ch}_'+suffix));a=next(q.GetPosition() for q in fps[f'U50{ch}'].Pads() if q.GetNetname()==net);z=next(q.GetPosition() for q in fps['J501' if ch==1 else 'J503'].Pads() if q.GetNetname()==net)
 ok=False
 for lid in [preferred,1-preferred]:
  print('A* motor group',net,'layer',lid,flush=True);ok=router.route_astar(net,pcbnew.ToMM(a.x),pcbnew.ToMM(a.y),lid,pcbnew.ToMM(z.x),pcbnew.ToMM(z.y),lid,bbox=(90,115,137,151.7),allow_in2=False,width=.5)
  if ok:break
 results.append({'net':net,'layer':lid,'width_mm':.5,'success':ok})
 assert ok,'Group reroute failed; board not saved: '+net
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'motor-group-routing.json').write_text(json.dumps({'removed_route_ids':removed,'routes':results},indent=2));print('All eight motor nets routed automatically with current-sized layer transitions.',flush=True)
