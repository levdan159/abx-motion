from pathlib import Path
import pcbnew,json,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
from shapely.geometry import LineString,box,Point
from shapely.ops import polygonize,unary_union
R=Path(__file__).resolve().parents[2];O=R/'variants/ABX-Motion-ETH';A=R/'work/ethernet-rev1.2b-20261023'
b=pcbnew.LoadBoard(str(O/'abx-motion-eth-placement.kicad_pcb'))
parts=json.loads((O/'layout-review/parts.json').read_text());moves={p['ref'] for p in json.loads((O/'layout-review/moved-parts.json').read_text())}
fs={f.GetReference():f for f in b.GetFootprints()}
def outline(f,layer):
 ls=[]
 for g in f.GraphicalItems():
  if g.GetClass()=='PCB_SHAPE' and g.GetLayer()==layer and g.GetShapeStr()=='Line':
   a,z=g.GetStart(),g.GetEnd();ls.append(LineString([(a.x/1e6,a.y/1e6),(z.x/1e6,z.y/1e6)]))
 ps=list(polygonize(ls));return unary_union(ps) if ps else None
def bounds(f):
 p=outline(f,pcbnew.F_CrtYd)
 if p is not None and not p.is_empty:return p
 bb=f.GetBoundingBox(False,False)
 return box(bb.GetLeft()/1e6,bb.GetTop()/1e6,bb.GetRight()/1e6,bb.GetBottom()/1e6)
polys={r:bounds(f) for r,f in fs.items() if r not in ['LOGO1','LOGO2','PWR_ETH_RESERVE']}
overlap=[]
refs=list(polys)
for i,r in enumerate(refs):
 for s in refs[i+1:]:
  if r not in parts and s not in parts and r not in moves and s not in moves:continue
  p=polys[r].intersection(polys[s])
  if p.area>.0001:overlap.append(dict(a=r,b=s,area=round(p.area,4)))
rf=box(77,32.25,125,68.25)
rfhits=[]
for r in parts:
 p=polys[r].intersection(rf)
 if p.area>.0001:rfhits.append(dict(ref=r,area=round(p.area,4)))
report=dict(courtyard_overlaps=overlap,new_parts_inside_15mm_antenna_envelope=rfhits,
            extra_antenna_clearance_waived_by_user=True,
            stage='PLACEMENT ONLY - NO ROUTING OR ELECTRICAL INTEGRATION',
            ethernet_supply_reservation_mm=[131,54,156,58.5],
            ethernet_supply_test_point_mm=[133.5,56.25],
            jack_body_bounds=list(outline(fs['J801'],pcbnew.F_Fab).bounds),
            jack_height_mm=13.5,board_edge_y_mm=48)
(O/'layout-review/geometry.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=1))

def plot(name,xlim,ylim,large=False):
 fig,ax=plt.subplots(figsize=(15,11) if large else (15,10))
 fig.patch.set_facecolor('#f3f5f6');ax.set_facecolor('#eaf0e9')
 ax.add_patch(Rectangle((45,48),157,105,fill=False,lw=2,color='#355746'))
 # Existing copper is muted so this figure describes physical placement only.
 for t in b.GetTracks():
  if t.GetClass()!='PCB_TRACK':continue
  a,z=t.GetStart(),t.GetEnd();xs=[a.x/1e6,z.x/1e6];ys=[a.y/1e6,z.y/1e6]
  if max(xs)<xlim[0] or min(xs)>xlim[1] or max(ys)<ylim[0] or min(ys)>ylim[1]:continue
  ax.plot(xs,ys,color='#5d7064',alpha=.09,lw=.5,zorder=1)
 for r,f in fs.items():
  if r=='PWR_ETH_RESERVE':continue
  p=polys.get(r)
  if p is None:continue
  x0,y0,x1,y1=p.bounds
  if x1<xlim[0] or x0>xlim[1] or y1<ylim[0] or y0>ylim[1]:continue
  color='#007e9e' if r in parts else '#b06013' if r in moves else '#6c7c73'
  for pp in [p] if p.geom_type=='Polygon' else p.geoms:
   xx,yy=pp.exterior.xy;ax.fill(xx,yy,color=color,alpha=.11,zorder=2);ax.plot(xx,yy,color=color,lw=.65,zorder=3)
  for pad in f.Pads():
   pos=pad.GetPosition();sz=pad.GetSize();x,y=pos.x/1e6,pos.y/1e6
   ax.add_patch(Circle((x,y),min(sz.x,sz.y)/2e6,color='#d4ac4c',alpha=.85,zorder=4))
  pos=f.GetPosition();x,y=pos.x/1e6,pos.y/1e6
  if large or r in ['U3','U1','U2','L1','J801','U801','Y801','U803','Q1']:
   ax.text((x0+x1)/2,(y0+y1)/2,r,fontsize=6 if r in parts and r not in ['J801','U801'] else 8,
           ha='center',va='center',weight='bold',color=color,zorder=5)
  if r in ['J801','U801','U3']:
   labels={'J801':'RJ45 + MAGNETICS','U801':'W5500','U3':'ESP32-S3'}
   ax.text((x0+x1)/2,y1+.65,labels[r],ha='center',fontsize=9,color=color,weight='bold')
 ax.annotate('Extra antenna clearance waived\nWi-Fi performance to be measured',(112,51),(106,44.5),ha='right',fontsize=8,color='#ab3d6c',arrowprops=dict(arrowstyle='->',color='#ab3d6c'))
 ax.add_patch(Rectangle((131,54),25,4.5,fill=False,edgecolor='#8b49ac',ls='--',lw=1.5))
 ax.text(147.75,56.25,'3V3 ETH SUPPLY RESERVE',fontsize=7,ha='center',color='#8b49ac',weight='bold')
 ax.annotate('CABLE EXIT',(120.5,46),(120.5,42.7),ha='center',fontsize=10,weight='bold',color='#007e9e',arrowprops=dict(arrowstyle='<-',color='#007e9e',lw=2))
 ax.set_xlim(xlim);ax.set_ylim(ylim[1],ylim[0]);ax.set_aspect('equal');ax.grid(alpha=.15)
 ax.set_xlabel('PCB X (mm)');ax.set_ylabel('PCB Y (mm)')
 ax.set_title('ABX-Motion-ETH · Rev 1.2b placement candidate',loc='left',fontsize=17,weight='bold',pad=15)
 fig.text(.12,.025,'Blue: new Ethernet parts     Amber: locally moved parts     Grey: existing placement\nPlacement only. Existing copper has not been rerouted. Power selection and electrical integration remain open.',fontsize=10,color='#43564b')
 fig.savefig(O/'layout-review'/name,dpi=150,bbox_inches='tight');plt.close(fig)
plot('placement-detail.png',(76,174),(41,101),True)
plot('placement-overview.png',(42,205),(40,156))
