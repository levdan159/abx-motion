from pathlib import Path
import json,collections,hashlib,xml.etree.ElementTree as ET
import pcbnew
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
P=Path('variants/ABX-Motion-ETH');O=Path('work/ethernet-routing-20261024');D=P/'layout-review'
b=pcbnew.LoadBoard(str(P/'abx-motion-eth-placement.kicad_pcb'));a=pcbnew.LoadBoard(str(O/'before/board.kicad_pcb'))
fs={f.GetReference():f for f in b.GetFootprints()};afs={f.GetReference():f for f in a.GetFootprints()};power=set(json.load(open(O/'power-refs.json')))
oldpads={(f.GetReference(),p.GetNumber(),p.m_Uuid.AsString()):p.GetNetname() for f in a.GetFootprints() for p in f.Pads() if f.GetReference() not in power}
newpads={(f.GetReference(),p.GetNumber(),p.m_Uuid.AsString()):p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if f.GetReference() not in power}
assert oldpads==newpads,'Original pad nets changed'
assert all(fs[r].GetPosition()==f.GetPosition() and fs[r].GetOrientationDegrees()==f.GetOrientationDegrees() for r,f in afs.items()),'Component moved'
assert {(z.m_Uuid.AsString(),z.GetNetname(),z.GetLayer()) for z in a.Zones()}=={(z.m_Uuid.AsString(),z.GetNetname(),z.GetLayer()) for z in b.Zones()},'Zone net or layer changed'
netlist=ET.parse(O/'with-power-netlist.xml');expected={}
for net in netlist.findall('.//nets/net'):
 for n in net.findall('node'):
  if n.get('ref') in power:expected[(n.get('ref'),n.get('pin'))]=net.get('name')
for r in power:
 for p in fs[r].Pads():assert p.GetNetname()==expected[(r,p.GetNumber())],(r,p.GetNumber(),p.GetNetname(),expected.get((r,p.GetNumber())))
assert hashlib.sha256(Path('abx-motion.kicad_pcb').read_bytes()).hexdigest()=='51a583987cc928cb9c5e47a8bd627dcd8717c2d7bf8e899feedf9d6ab6bdb1d0'
report=json.load(open(O/'final-drc.json'));ct=collections.Counter(v['type'] for v in report['violations'])
status=dict(stage='ROUTING IN PROGRESS',integrated_power_footprints=sorted(power),remaining_unintegrated_ethernet_footprints=49,
 original_pad_nets_preserved=True,original_positions_preserved=True,original_zone_net_layer_preserved=True,root_pcb_unchanged=True,power_pads_match_exported_schematic=True,
 stack=['F.Cu','In1.Cu GND plane','In2.Cu split power and short signal underpasses','B.Cu'],
 drc_counts=dict(ct),defined_net_opens=len(report['unconnected_items']),erc_violations=0,
 manufacturing_ready=False,next='Integrate and route controller, crystal, magjack, reset and SPI isolation; establish final isolation keepouts; full release validation')
(D/'routing-progress.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status,indent=2))
colors={0:'#d34c42',2:'#3279c2',6:'#9a52ab',4:'#79a360'}
for name,xl,yl in [('routing-supply.png',(130,160),(49,65)),('routing-overview.png',(79,161),(47,103))]:
 fig,ax=plt.subplots(figsize=(15,9));ax.set_facecolor('#152031');fig.patch.set_facecolor('#152031')
 for t in b.GetTracks():
  layer=t.GetLayer()
  if t.GetClass()=='PCB_VIA':
   v=t.GetPosition();x,y=v.x/1e6,v.y/1e6
   if xl[0]<=x<=xl[1] and yl[0]<=y<=yl[1]:ax.add_patch(Circle((x,y),t.GetWidth(pcbnew.F_Cu)/2e6,facecolor='#c7a852',edgecolor='#d2c390',lw=.5));ax.add_patch(Circle((x,y),t.GetDrillValue()/2e6,facecolor='#152031'))
  elif layer in colors:
   x,y=t.GetStart(),t.GetEnd();ax.plot([x.x/1e6,y.x/1e6],[x.y/1e6,y.y/1e6],color=colors[layer],lw=max(.5,t.GetWidth()/1e6*3),alpha=.85)
 for r,f in fs.items():
  pos=f.GetPosition();x,y=pos.x/1e6,pos.y/1e6
  if not(xl[0]-3<x<xl[1]+3 and yl[0]-3<y<yl[1]+3):continue
  for pad in f.Pads():
   z=pad.GetBoundingBox();ax.add_patch(Rectangle((z.GetLeft()/1e6,z.GetTop()/1e6),z.GetWidth()/1e6,z.GetHeight()/1e6,facecolor='#c6a75b',alpha=.75))
  if r in power or r in ['U3','U801','J801','U804','U1','U2','L1']:
   ax.text(x,y-.45,r,ha='center',va='bottom',color='white',fontsize=8,bbox=dict(facecolor='#152031',alpha=.6,edgecolor='none',pad=.3))
 ax.set_xlim(xl);ax.set_ylim(yl[1],yl[0]);ax.set_aspect('equal');ax.tick_params(colors='white');ax.grid(alpha=.12);ax.set_title('Actual routed copper — Rev 1.2b Ethernet draft\nRed: front | Blue: rear | Purple: In2 | Ground fills hidden for clarity',color='white')
 fig.tight_layout();fig.savefig(D/name,dpi=160);plt.close(fig)
