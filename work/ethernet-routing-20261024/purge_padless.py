"""Remove bounded isolated copper components with no connected component pad.
Includes conductive zone connectivity via native GetConnectedItems after refill.
"""
from pathlib import Path
import pcbnew,json,collections,re
R=Path.cwd();A=R/'work/ethernet-routing-20261024';O=R/'variants/ABX-Motion-ETH';P=O/'abx-motion-eth-placement.kicad_pcb';b=pcbnew.LoadBoard(str(P));pcbnew.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();c=b.GetConnectivity();uid=lambda t:t.m_Uuid.AsString();ts={uid(t):t for t in b.GetTracks()};seen=set();removed={}
def scope(t):
 ps=[t.GetPosition()] if t.GetClass()=='PCB_VIA' else [t.GetStart(),t.GetEnd()]
 return all(80e6<=p.x<=180e6 and 48e6<=p.y<=114e6 for p in ps)
for u,t in ts.items():
 if u in seen or not scope(t) or not t.GetNetname() or re.fullmatch('AX[123]_[AB][12]',t.GetNetname()) or t.GetNetname().startswith('/DC_Motor_'):continue
 comp=[t]+list(c.GetConnectedItems(t));ids={uid(q) for q in comp};seen|=ids
 if any(q.GetClass()=='PAD' for q in comp):continue
 cu=[q for q in comp if q.GetClass() in ['PCB_TRACK','PCB_VIA']];cu={uid(q):q for q in cu}
 if not cu or not all(scope(q) for q in cu.values()):continue
 for v,q in cu.items():removed[v]=dict(net=q.GetNetname(),kind=q.GetClass(),reason='native conductive component has no component pads, including zone connectivity')
hold=[ts[u] for u in removed]
for t in hold:b.Remove(t)
pcbnew.SaveBoard(str(A/'padless-clean.kicad_pcb'),b);P.write_bytes((A/'padless-clean.kicad_pcb').read_bytes());(A/'padless-removals.json').write_text(json.dumps(removed,indent=2)+'\n');print('Removed',len(removed),'padless copper objects',collections.Counter(q['net'] for q in removed.values()))
