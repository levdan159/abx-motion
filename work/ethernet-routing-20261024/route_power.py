"""First hand-planned supply routing pass; native DRC is the acceptance gate."""
from pathlib import Path
import pcbnew,json,collections
R=Path.cwd();A=R/'work/ethernet-routing-20261024';O=R/'variants/ABX-Motion-ETH';P=O/'abx-motion-eth-placement.kicad_pcb'
b=pcbnew.LoadBoard(str(A/'integrated-clean.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()};mm=lambda x,y:pcbnew.VECTOR2I(round(x*1e6),round(y*1e6));uid=lambda t:t.m_Uuid.AsString();new=[]
def xy(k):
 r,n=k.split('.');p=next(p for p in fs[r].Pads() if p.GetNumber()==n).GetPosition();return(p.x/1e6,p.y/1e6)
def route(net,pts,w=.2,layer='F.Cu',group=''):
 pts=[xy(p) if isinstance(p,str) else p for p in pts]
 for a,z in zip(pts,pts[1:]):
  if a==z:continue
  t=pcbnew.PCB_TRACK(b);t.SetStart(mm(*a));t.SetEnd(mm(*z));t.SetLayer(b.GetLayerID(layer));t.SetWidth(round(w*1e6));t.SetNet(b.FindNet(net));b.Add(t);new.append(dict(uuid=uid(t),kind='segment',net=net,start=a,end=z,width_mm=w,layer=layer,group=group))
def via(net,p,d=.5,drill=.25,group=''):
 v=pcbnew.PCB_VIA(b);v.SetPosition(mm(*p));v.SetWidth(round(d*1e6));v.SetDrill(round(drill*1e6));v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu);v.SetNet(b.FindNet(net));v.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED);v.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED);b.Add(v);new.append(dict(uuid=uid(v),kind='via',net=net,position=p,diameter_mm=d,drill_mm=drill,group=group))
# Actual existing planes, rather than an assumed two-layer stack.
for net,p in [('+BATT',(155.5,54.775))]:
 assert any(z.GetNetname()==net and z.HitTestFilledArea(pcbnew.In2_Cu,mm(*p)) for z in b.Zones()),('Source point is outside intended power plane',net,p)
route('+BATT',['C822.1','C821.1'],.6,group='input bulk')
route('+BATT',['C821.1',(150.325,54.1),'C823.2'],.4,group='input bulk to HF')
route('+BATT',['C823.2',(147.575,54.4375),'U802.4'],.25,group='VIN hot loop')
route('GND',['C823.1',(145.5,54.1),'U802.9'],.3,group='front hot-loop return')
route('GND',['U802.9',(145.5,57.9)],.3,group='IC ground stitch');via('GND',(145.5,57.9),group='IC ground stitch')
via('+BATT',(155.5,54.775),.6,.3,group='protected battery plane feed');route('+BATT',[(155.5,54.775),'C822.1'],.6,group='protected battery plane feed')
route('GND',['C821.2','C822.2'],.6,group='input return')
for r in ['C821','C822']:
 p=xy(r+'.2');v=(p[0],58.8);route('GND',[p,v],.4,group='input return');via('GND',v,.6,.3,group='input return')
route('ETH_SW',['U802.5','C824.2',(141.5,54.92),'L801.2'],.25,group='small SW island')
route('ETH_BOOT',['U802.6',(143.62,56.1),'C824.1'],.15,group='bootstrap')
route('ETH_VCC_INT',['U802.7',(143.92,56.6),'C825.1'],.15,group='local VCC bypass')
via('ETH_VCC_INT',(144.05,56.6),group='RT fixed-frequency bridge')
via('ETH_VCC_INT',(147,57.2),group='RT fixed-frequency bridge')
route('ETH_VCC_INT',['U802.1',(146.8875,57.0875),(147,57.2)],.15,group='RT fixed-frequency bridge')
route('ETH_VCC_INT',[(147,57.2),(146.4,57.2),(145.8,56.6),(144.05,56.6)],.15,'B.Cu','RT fixed-frequency bridge')
route('GND',['C825.2',(142.65,58.08)],.25,group='VCC ground stitch');via('GND',(142.65,58.08),group='VCC ground stitch')
route('3V3_ETH',['L801.1',(136.975,54.775),'C827.2','C826.2'],.6,group='output bus')
for r in ['C826','C827']:
 p=xy(r+'.1');v=(p[0],58.4);route('GND',[p,v],.4,group='output ground stitches');via('GND',v,group='output ground stitches')
route('3V3_ETH',['C827.2',(136.4,53.7)],.35,group='output plane change');via('3V3_ETH',(136.4,53.7),group='output plane change')
route('3V3_ETH',['U802.8',(144.6,58.2)],.15,group='quiet output sense');via('3V3_ETH',(144.6,58.2),group='quiet output sense')
route('3V3_ETH',[(144.6,58.2),(143.6,59.2),(138.2,59.2),(137.8,58.8),(137.8,55.1),(136.4,53.7)],.15,'B.Cu','quiet output sense')
route('3V3_ETH',[(136.4,53.7),(155.9,53.7),(157,54.8),(157,55)],.3,'B.Cu','output test point branch');via('3V3_ETH',(157,55),group='output test point branch');route('3V3_ETH',[(157,55),'TP_ETH_3V3.1'],.3,group='output test point branch')
# Enable follows the real main3V3 rail. A short In2 power branch uses the actual
# distribution layer; In1 GND is never used for signal/power tracks.
via('+3V3',(140.8,77.3),group='main3V3 regulator source');route('+3V3',['U2.5',(140.55,77.55),(140.8,77.3)],.2,group='main3V3 regulator source');via('+3V3',(147.8,57.5),group='main3V3 enable feed')
via('+3V3',(144.15,74.2),group='main3V3 PWM underpass');via('+3V3',(145.55,72.8),group='main3V3 PWM underpass')
route('+3V3',[(140.8,77.3),(141.05,77.3),(144.15,74.2)],.2,'B.Cu','main3V3 enable feed')
route('+3V3',[(144.15,74.2),(145.55,72.8)],.2,'In2.Cu','main3V3 PWM underpass')
route('+3V3',[(145.55,72.8),(154,64.35),(154,60),(151,57),(147.8,57),(147.8,57.5)],.2,'B.Cu','main3V3 enable feed')
route('+3V3',['R817.1',(147.52,57.22),(147.8,57.5)],.15,group='main3V3 enable feed')
route('ETH_BUCK_EN',['U802.3',(146.95,56.1),(147.45,55.6),(148.48,55.6),'R817.2'],.15,group='enable')
route('ETH_BUCK_EN',['R817.2',(149.3,56.4),(149.3,57.37),(148.7,57.37),(147.72,58.35),'R818.1'],.15,group='enable pull-down')
route('GND',['R818.2',(148.68,58),(149.7,58)],.25,group='enable pull-down ground');via('GND',(149.7,58),group='enable pull-down ground')
# Restore the moved main3V3 probe using the new main3V3 distribution branch.
route('+3V3',['TP_3V3_1.1',(143.5,56),(148.5,56),(148.5,56.8),(147.8,57.5)],.2,'In2.Cu','main3V3 moved test pad')

pcbnew.SaveBoard(str(A/'power-first-route.kicad_pcb'),b);P.write_bytes((A/'power-first-route.kicad_pcb').read_bytes());(A/'power-routes.json').write_text(json.dumps(new,indent=2)+'\n');print('Added',collections.Counter(q['kind'] for q in new),'across',len({q['group'] for q in new}),'supply routing groups.')
