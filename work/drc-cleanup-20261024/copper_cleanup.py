from pathlib import Path
import pcbnew,json,collections,sys
R=Path.cwd();O=R/'work/drc-cleanup-20261024';b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));pcbnew.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();c=b.GetConnectivity();uid=lambda t:t.m_Uuid.AsString()
report=json.loads((O/(sys.argv[1] if len(sys.argv)>1 else 'before-drc.json')).read_text());requested={v['items'][0]['uuid']:v['type'] for v in report['violations'] if v['type'] in ['via_dangling','track_dangling']}
ts={uid(t):t for t in b.GetTracks()};pads={uid(p):p for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode()>0};objs=ts|pads;adj={u:set() for u in objs}
for u,t in objs.items():
 for q in list(c.GetConnectedTracks(t))+list(c.GetConnectedPads(t)):
  v=uid(q)
  if v in adj and v!=u:adj[u].add(v);adj[v].add(u)
def padgroups(board):
 conn=board.GetConnectivity();ps={uid(p):p for f in board.GetFootprints() for p in f.Pads() if p.GetNetCode()>0};seen=set();groups=[]
 for u,p in ps.items():
  if u in seen:continue
  group={u}|{uid(v) for v in conn.GetConnectedItems(p) if v.GetClass()=='PAD' and uid(v) in ps};seen|=group;groups.append(sorted(group))
 return sorted(groups)
before=padgroups(b);active=set(adj);removed={}
def nonbridge(u):
 ns=adj[u]&active
 if len(ns)<=1:return True
 todo=[next(iter(ns))];seen={u}
 while todo:
  v=todo.pop()
  if v in seen:continue
  seen.add(v);todo.extend((adj[v]&active)-seen)
  if ns<=seen:return True
 return False
for _ in range(20):
 n=0
 for u,typ in requested.items():
  if u not in active or not nonbridge(u):continue
  t=ts[u]
  if typ=='via_dangling':
   # Native DRC already establishes no functional layer transfer. Direct
   # neighborhood must also be removable without splitting conductive graph.
   reason='Native one-layer/unconnected via; graph nonbridge; pad groups verified'
  else:reason='Native dangling segment; graph nonbridge; pad groups verified'
  active.remove(u);removed[u]=dict(net=t.GetNetname(),kind=t.GetClass(),reason=reason);n+=1
 if not n:break
hold=[ts[u] for u in removed]
for t in hold:b.Remove(t)
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity()
after=padgroups(b);assert before==after,'Removal changes native pad connectivity'
pcbnew.SaveBoard(str(O/'copper-clean.kicad_pcb'),b)
(R/'abx-motion.kicad_pcb').write_bytes((O/'copper-clean.kicad_pcb').read_bytes())
(O/('copper-removals-'+(sys.argv[2] if len(sys.argv)>2 else 'first')+'.json')).write_text(json.dumps(removed,indent=2)+'\n');(O/'pending-copper.json').write_text(json.dumps({u:requested[u] for u in requested if u not in removed},indent=2)+'\n')
print('Removed',len(removed),'of',len(requested),'flagged copper objects; native pad groups unchanged; pending',len(requested)-len(removed),flush=True)
