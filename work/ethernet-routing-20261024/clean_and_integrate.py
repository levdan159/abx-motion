"""Assign ONLY schematic-defined power nets; trim copper conflicting with new pads.
All trimmed copper is logged for reconnection. No region-wide copper deletion.
"""
from pathlib import Path
import json,math,sys,collections,re,xml.etree.ElementTree as ET,hashlib
import pcbnew
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union
R=Path.cwd();A=R/'work/ethernet-routing-20261024';O=R/'variants/ABX-Motion-ETH';P=O/'abx-motion-eth-placement.kicad_pcb'
b=pcbnew.LoadBoard(str(A/'before/board.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()};uid=lambda t:t.m_Uuid.AsString();mm=lambda v:(v.x/1e6,v.y/1e6);vec=lambda p:pcbnew.VECTOR2I(round(p[0]*1e6),round(p[1]*1e6))
oldtracks={uid(t):t for t in b.GetTracks()};oldpadnets={(r,p.GetNumber()):p.GetNetname() for r,f in fs.items() for p in f.Pads() if p.GetNumber()};oldzones=[(uid(z),z.GetNetname(),list(z.GetLayerSet().Seq())) for z in b.Zones()]
x=ET.parse(A/'with-power-netlist.xml').getroot();comps={c.attrib['ref']:c for c in x.findall('./components/comp')};pn={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in x.findall('./nets/net') for n in net.findall('node')};refs=set(json.loads((A/'power-refs.json').read_text()))
for r in refs:
 f=fs[r];co=comps[r];f.SetPath(pcbnew.KIID_PATH(co.find('sheetpath').attrib['tstamps']+co.findtext('tstamps')))
 for p in f.Pads():
  netname=pn[r,p.GetNumber()];net=b.FindNet(netname)
  if net is None or net.GetNetCode()<0:net=pcbnew.NETINFO_ITEM(b,netname);b.Add(net)
  p.SetNet(net)
# Use every new and previously moved pad as a bounded cleanup obstacle.
new=set(json.loads((O/'layout-review/parts.json').read_text()));moved={q['ref'] for q in json.loads((O/'layout-review/moved-parts.json').read_text())};pads=[]
for r in sorted(new|moved):
 for p in fs[r].Pads():
  bb=p.GetBoundingBox();geom=box(bb.GetLeft()/1e6,bb.GetTop()/1e6,bb.GetRight()/1e6,bb.GetBottom()/1e6)
  pads.append((r,p,geom))
removed={};fragments=[];keep=[]
for u,t in oldtracks.items():
 n=t.GetNetname();hits=[]
 if t.GetClass()=='PCB_VIA':
  pt=Point(mm(t.GetPosition()));rad=t.GetWidth(pcbnew.F_Cu)/2e6
  for r,p,g in pads:
   foreign=n!=p.GetNetname() or not n
   if foreign and pt.distance(g)<rad+.17-1e-8:hits.append([r,p.GetNumber(),'foreign copper / pad clearance'])
   if p.GetDrillSize().x:
    if pt.distance(Point(mm(p.GetPosition())))<t.GetDrillValue()/2e6+max(p.GetDrillSize().x,p.GetDrillSize().y)/2e6+.254:hits.append([r,p.GetNumber(),'drill clearance'])
  if hits:removed[u]=dict(kind='via',net=n,position=mm(t.GetPosition()),conflicts=hits,reason='old layer-transfer/stitch point conflicts with new placement; review/reconnect required');keep.append(t)
 else:
  line=LineString([mm(t.GetStart()),mm(t.GetEnd())]);w=t.GetWidth()/1e6;obs=[]
  for r,p,g in pads:
   if n and n==p.GetNetname():continue
   if p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH:
    hole=Point(mm(p.GetPosition())).buffer(max(p.GetDrillSize().x,p.GetDrillSize().y)/2e6)
    if line.distance(hole)<w/2+.254:obs.append(hole.buffer(w/2+.255,quad_segs=8));hits.append([r,p.GetNumber(),'NPTH drill clearance on every copper layer'])
    continue
   if not p.IsOnLayer(t.GetLayer()):continue
   if line.distance(g)<w/2+.17-1e-8:obs.append(g.buffer(w/2+.171,quad_segs=4));hits.append([r,p.GetNumber(),'foreign copper / pad clearance'])
  if not hits:continue
  result=line.difference(unary_union(obs));chunks=[result] if result.geom_type=='LineString' else [q for q in result.geoms if q.geom_type=='LineString']
  removed[u]=dict(kind='segment',net=n,layer=b.GetLayerName(t.GetLayer()),start=mm(t.GetStart()),end=mm(t.GetEnd()),width_mm=w,conflicts=hits,reason='only conflicting interval removed; unaffected ends retained',retained=[]);keep.append(t)
  for ch in chunks:
   if ch.length<.08:continue
   a,z=list(ch.coords)[0],list(ch.coords)[-1];q=pcbnew.PCB_TRACK(b);q.SetStart(vec(a));q.SetEnd(vec(z));q.SetLayer(t.GetLayer());q.SetWidth(t.GetWidth());q.SetNet(t.GetNet());b.Add(q);fragments.append(q);removed[u]['retained'].append(dict(uuid=uid(q),start=a,end=z))
for t in keep:
 assert not re.fullmatch('AX[123]_[AB][12]',t.GetNetname()),'Unexpected stepper phase copper affected'
 assert t.GetClass()=='PCB_VIA' or t.GetLayer()!=pcbnew.In1_Cu,'Do not cut inner ground plane'
 b.Remove(t)
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
# Save natively now that unassigned draft pads no longer overlap retained copper.
pcbnew.SaveBoard(str(A/'integrated-clean.kicad_pcb'),b)
check=pcbnew.LoadBoard(str(A/'integrated-clean.kicad_pcb'));cf={f.GetReference():f for f in check.GetFootprints()}
assert all(p.GetNetname()==oldpadnets[r,p.GetNumber()] for r,f in cf.items() if r not in refs for p in f.Pads() if p.GetNumber()),'Unexpected pad net change'
assert all(p.GetNetname()==pn[r,p.GetNumber()] for r in refs for p in cf[r].Pads()),'Power net assignment mismatch'
assert oldzones==[(uid(z),z.GetNetname(),list(z.GetLayerSet().Seq())) for z in check.Zones()]
# All source copper not explicitly logged survives, with original net and geometry.
ct={uid(t):t for t in check.GetTracks()}
for u,t in oldtracks.items():
 if u in removed or u in stub:continue
 assert u in ct and t.GetNetname()==ct[u].GetNetname(),('Unlogged copper loss',u)
P.write_bytes((A/'integrated-clean.kicad_pcb').read_bytes())
report=dict(date='2026-10-24',schematic_integrated_refs=sorted(refs),all_other_pad_nets_preserved=True,zone_assignments_and_layers_preserved=True,collision_removals=removed,stub_removals=stub,retained_collision_free_fragments=len(fragments),cleanup_preserves_post_trim_component_pad_partitions=True,removed_original_vias=sum(v['kind']=='via' for v in removed.values()),removed_signal_stubs_and_redundant_vias=len(stub),affected_nets=sorted({v['net'] for v in removed.values()}),routing_required=True)
(A/'cleanup.json').write_text(json.dumps(report,indent=2)+'\n');print('Cleaned',len(removed),'colliding source objects; retained',len(fragments),'non-conflicting fragments; removed',len(stub),'proved signal stubs/redundant vias.')
