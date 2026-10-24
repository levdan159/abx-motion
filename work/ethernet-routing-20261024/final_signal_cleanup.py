from pathlib import Path
import pcbnew,json,re
p=Path('variants/ABX-Motion-ETH/abx-motion-eth-placement.kicad_pcb');b=pcbnew.LoadBoard(str(p));uid=lambda t:t.m_Uuid.AsString()
# Native cleanup after collision trimming: signals only, preserve every connected
# component-pad partition. Plane/stitch/thermal/power copper is not swept.
b.BuildConnectivity();c=b.GetConnectivity();zonenets={z.GetNetname() for z in b.Zones()}
def signal(n):return bool(n) and n not in zonenets and not n.startswith(('+','3V3_ETH','ETH_','/DC_Motor_','unconnected-')) and not re.fullmatch('AX[123]_[AB][12]',n)
tracks={uid(t):t for t in b.GetTracks() if signal(t.GetNetname())};pp={uid(p):p for f in b.GetFootprints() for p in f.Pads() if signal(p.GetNetname())};objs=tracks|pp;adj={u:set() for u in objs}
for u,t in objs.items():
 for q in list(c.GetConnectedTracks(t))+list(c.GetConnectedPads(t)):
  v=uid(q)
  if v in adj and v!=u:adj[u].add(v);adj[v].add(u)
def scope(t):
 ps=[t.GetPosition()] if t.GetClass()=='PCB_VIA' else [t.GetStart(),t.GetEnd()]
 return all(80e6<=p.x<=180e6 and 48e6<=p.y<=102e6 for p in ps)
can={u for u,t in tracks.items() if scope(t)};active=set(adj);stub={};done=set()
for u in adj:
 if u in done:continue
 comp=set();todo=[u]
 while todo:
  v=todo.pop()
  if v in comp:continue
  comp.add(v);todo.extend(adj[v]-comp)
 done|=comp
 if not comp&pp.keys() and comp<=can:
  for v in comp:stub[v]=dict(net=tracks[v].GetNetname(),kind=tracks[v].GetClass(),reason='isolated signal copper with no component pad');active.remove(v)
def partition(nodes):
 seen=set();out=[]
 for p in pp:
  if p in seen:continue
  todo=[p];comp=set()
  while todo:
   u=todo.pop()
   if u in comp:continue
   comp.add(u);todo.extend((adj[u]&nodes)-comp)
  seen|=comp;out.append(sorted(comp&pp.keys()))
 return sorted(out)
basepart=partition(set(adj))
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
for iteration in range(50):
 changed=0
 for u in sorted(can&active):
  t=tracks[u];ns=adj[u]&active
  if t.GetClass()=='PCB_TRACK':
   if not (len(ns)<=1 or c.TestTrackEndpointDangling(t,False)):continue
   reason='dangling signal stub; nonbridge proof'
  else:
   if ns&pp.keys():continue
   qq=[objs[v] for v in ns]
   if any(q.GetClass()!='PCB_TRACK' for q in qq) or len({q.GetLayer() for q in qq})>1:continue
   reason='signal via without layer transfer; nonbridge proof'
  if not nonbridge(u):continue
  active.remove(u);stub[u]=dict(net=t.GetNetname(),kind=t.GetClass(),reason=reason);changed+=1
 if not changed:break
assert basepart==partition(active),'Cleanup changed connected pad groups'
hold=[tracks[u] for u in stub]
for t in hold:b.Remove(t)

b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(p),b)
Path('work/ethernet-routing-20261024/final-stub-removals.json').write_text(json.dumps(stub,indent=2)+'\n');print('Removed',len(stub),'proved redundant signal objects')
