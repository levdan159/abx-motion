import pcbnew as p,pathlib,json,hashlib,csv,xml.etree.ElementTree as E
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=pathlib.Path.cwd();v=r/'work/rev-1.2-relay-bottom-right/review';c=json.loads((v/'changes.json').read_text());fig,axes=plt.subplots(1,2,figsize=(13,7));results={}
for ax,name,path in zip(axes,['Before connector shift','After connector shift'],[v/'before.kicad_pcb',r/'abx-motion.kicad_pcb']):
 b=p.LoadBoard(str(path));grid=np.ones((255,210),dtype=bool)
 for f in b.GetFootprints():
  if f.GetLayer()!=p.F_Cu or f.GetReference().startswith('LOGO'):continue
  box=f.GetBoundingBox(False,False);x=p.ToMM(box.GetX());y=p.ToMM(box.GetY());w=p.ToMM(box.GetWidth());h=p.ToMM(box.GetHeight())
  if x<194 and x+w>130 and y<153 and y+h>103:
   ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='steelblue',lw=.7));ax.text(x+w/2,y+h/2,f.GetReference(),ha='center',va='center',fontsize=6)
  # ROI 136..157, 104..129.5; 0.25 mm keepout around physical bounding boxes
  x0=max(0,int(np.floor((x-.25-136)*10)));x1=min(210,int(np.ceil((x+w+.25-136)*10)))
  y0=max(0,int(np.floor((y-.25-104)*10)));y1=min(255,int(np.ceil((y+h+.25-104)*10)))
  if x1>x0 and y1>y0:grid[y0:y1,x0:x1]=False
 heights=[0]*210;best=(0,0,0,0,0)
 for row in range(255):
  heights=[heights[j]+1 if grid[row,j] else 0 for j in range(210)];stack=[]
  for j in range(211):
   hh=heights[j] if j<210 else 0;start=j
   while stack and stack[-1][1]>hh:
    pos,h0=stack.pop();area=h0*(j-pos)
    if area>best[0]:best=(area,pos,row-h0+1,j-pos,h0)
    start=pos
   if not stack or stack[-1][1]<hh:stack.append((start,hh))
 _,xx,yy,ww,hh=best;rect=[136+xx/10,104+yy/10,ww/10,hh/10];results[name]={'empty_rectangle_mm':rect,'area_mm2':ww*hh/100}
 ax.add_patch(Rectangle((rect[0],rect[1]),rect[2],rect[3],facecolor='limegreen',alpha=.25,edgecolor='green'));ax.set(xlim=(130,194),ylim=(153,103),title=name,xlabel='Board X (mm)',ylabel='Board Y (mm)');ax.set_aspect('equal');ax.grid(alpha=.15)
fig.suptitle('Relay bay: physical component envelopes; green = largest empty rectangle in fixed expansion ROI')
fig.tight_layout();fig.savefig(v/'relay-bay-before-after.png',dpi=160);(v/'space-audit.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
