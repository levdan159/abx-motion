"""Illustrative routing study only. Never emits PCB copper."""
from pathlib import Path
import pcbnew,json,ast
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
from shapely.geometry import LineString,box
from shapely.ops import polygonize,unary_union
R=Path(__file__).resolve().parents[2];O=R/'variants/ABX-Motion-ETH'
ns=globals();tree=ast.parse((R/'work/ethernet-rev1.2b-20261023/review.py').read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['outline','bounds']],type_ignores=[]),'geometry','exec'),ns)
b=pcbnew.LoadBoard(str(O/'abx-motion-eth-placement.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()};parts=json.loads((O/'layout-review/parts.json').read_text())
def xy(key):
 r,n=key.split('.');p=next(p for p in fs[r].Pads() if p.GetNumber()==n).GetPosition();return(p.x/1e6,p.y/1e6)
def base(ax,xlim,ylim):
 for r,f in fs.items():
  if r in ['LOGO1','LOGO2']:continue
  p=bounds(f);x0,y0,x1,y1=p.bounds
  if x1<xlim[0] or x0>xlim[1] or y1<ylim[0] or y0>ylim[1]:continue
  color='#117d95' if r in parts else '#7a817e'
  for pp in [p] if p.geom_type=='Polygon' else p.geoms:
   xx,yy=pp.exterior.xy;ax.fill(xx,yy,color=color,alpha=.07);ax.plot(xx,yy,color=color,lw=.8)
  ax.text((x0+x1)/2,(y0+y1)/2,r,fontsize=8 if r.startswith(('U','L','Q')) else 6.6,color=color,ha='center',va='center',weight='bold',clip_on=True)
  for pad in f.Pads():
   pos=pad.GetPosition();x,y=pos.x/1e6,pos.y/1e6;s=pad.GetSize();angle=pad.GetOrientationDegrees()%180
   w,h=s.x/1e6,s.y/1e6
   if abs(angle-90)<1:w,h=h,w
   ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,fc='#d6ba6b',ec='none',alpha=.55))
 ax.set_xlim(xlim);ax.set_ylim(ylim[1],ylim[0]);ax.set_aspect('equal');ax.set_facecolor('#f4f7f5');ax.grid(alpha=.12);ax.set_ylabel('PCB Y (mm)');ax.set_xlabel('PCB X (mm)')
def path(ax,pts,color,label=None,ls='-',lw=1.7):
 ax.plot([x for x,y in pts],[y for x,y in pts],color=color,lw=lw,ls=ls,label=label,zorder=5)
def via(ax,p,c):ax.add_patch(Circle(p,.25,fc='white',ec=c,lw=1.1,zorder=6))
fig,(a,z)=plt.subplots(2,1,figsize=(15,12),height_ratios=[.9,1.5]);fig.patch.set_facecolor('white')
base(a,(130.5,160),(52,61.5))
path(a,[xy('C822.1'),xy('C821.1'),xy('C823.2'),(147.575,54.8),(146.76,55.6125),xy('U802.4')],'#ba3d32','VIN / compact input loop')
path(a,[xy('C823.1'),(145.5,54.1),(145.5,56.25),xy('U802.9')],'#4067ae','Front GND return')
path(a,[xy('U802.5'),xy('C824.2'),(141.5,54.92),xy('L801.2')],'#ce8e0b','SW / keep small')
path(a,[xy('U802.6'),xy('C824.1')],'#7b4da1','BOOT')
path(a,[xy('U802.7'),(144.0,56.7),xy('C825.1')],'#734d2c','VCC; rear bridge to RT')
path(a,[xy('U802.1'),(147,57.2),(144,56.7)],'#734d2c',ls='--',lw=1.2)
for p in [(147,57.2),(144,56.7)]:via(a,p,'#734d2c')
path(a,[xy('L801.1'),xy('C827.2'),xy('C826.2')],'#258556','3V3 output')
path(a,[xy('U802.8'),(144.6,58.2),(143.7,59.1),(138.5,59.1),(136.4,57),(136.4,54.775)],'#b04b8b','Output sense (rear)',ls='--',lw=1.3)
via(a,(144.6,58.2),'#b04b8b')
a.annotate('Protected +BATT from Q1',(153.7,54.775),(155.5,53.3),fontsize=8,color='#ba3d32',arrowprops=dict(arrowstyle='->',color='#ba3d32'))
a.annotate('Output trunk to Ethernet\nrear crossing past C820',(133.9,54.775),(130.8,60.8),fontsize=8,color='#258556',arrowprops=dict(arrowstyle='->',color='#258556'))
a.legend(loc='lower center',bbox_to_anchor=(.5,-.38),ncol=4,fontsize=8,frameon=False)
a.set_title('Buck routing study — local loops and quiet pin escapes',loc='left',fontsize=13,weight='bold')
base(z,(101.5,133.5),(75,96))
# Broad strategy lines, not individual solved traces or a clearance proof.
path(z,[(123.65,80.1),(123.65,77.5),(114.8,77.5),(114.8,82.3),(113.16,82.3)],'#285e9e','Grouped SPI on rear; retain GND bridges',ls='--',lw=2)
for p in [(120.9,80.1),(121.55,80.1),(122.2,80.2),(123.65,80.1)]:via(z,p,'#285e9e')
for n in [30,31]:
 p=xy('U801.'+str(n));path(z,[p,(p[0],80.4),(119.4,82.5)],'#ce8e0b',lw=1.2)
z.annotate('XI/XO area reserved\nFront clock first; no SPI below',(119.5,81.8),(123,91.5),fontsize=8,color='#9d720b',arrowprops=dict(arrowstyle='->',color='#9d720b'))
z.annotate('Main SPI / CS\nshort MCU branch',(104.5,80),(101.8,75.5),fontsize=8,color='#285e9e',arrowprops=dict(arrowstyle='->',color='#285e9e'))
z.annotate('CS-gated isolation\nreleases shared MISO',(110.3,82),(101.8,94.5),fontsize=8,color='#285e9e',arrowprops=dict(arrowstyle='->',color='#285e9e'))
z.annotate('Monitor + open-drain reset\nslow control can change layers',(112,90),(124,94.5),fontsize=8,color='#117d95',arrowprops=dict(arrowstyle='->',color='#117d95'))
z.legend(loc='lower center',bbox_to_anchor=(.5,-.14),fontsize=9,frameon=False)
z.set_title('SPI / clock / reset escape study — original logic stays stationary',loc='left',fontsize=13,weight='bold')
fig.suptitle('ABX-Motion-ETH · Rev 1.2b · proposed routing paths',fontsize=18,weight='bold',x=.08,ha='left')
fig.text(.08,.015,'ILLUSTRATIVE ONLY: guide lines/via locations are not copper, a solved route, or a DRC pass.\nAll new pads remain unconnected. Existing copper must be locally reconciled after schematic integration.',fontsize=10,color='#515c55')
fig.subplots_adjust(hspace=.55,top=.92,bottom=.10)
fig.savefig(O/'layout-review/power-routing-plan.png',dpi=160,bbox_inches='tight');plt.close(fig)
