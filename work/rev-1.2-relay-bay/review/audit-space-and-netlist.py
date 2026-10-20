import pcbnew as p,pathlib,json,hashlib,csv,xml.etree.ElementTree as E
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=pathlib.Path.cwd();v=r/'work/rev-1.2-relay-bay/review';c=json.loads((v/'changes.json').read_text());fig,axes=plt.subplots(1,2,figsize=(13,7));results={}
for ax,name,path in zip(axes,['Before (Rev 1.1d)','After (Rev 1.2-dev)'],[v/'before.kicad_pcb',r/'abx-motion.kicad_pcb']):
 b=p.LoadBoard(str(path));grid=np.ones((155,210),dtype=bool)
 for f in b.GetFootprints():
  if f.GetLayer()!=p.F_Cu or f.GetReference().startswith('LOGO'):continue
  box=f.GetBoundingBox(False,False);x=p.ToMM(box.GetX());y=p.ToMM(box.GetY());w=p.ToMM(box.GetWidth());h=p.ToMM(box.GetHeight())
  if x<194 and x+w>130 and y<153 and y+h>103:
   ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='steelblue',lw=.7));ax.text(x+w/2,y+h/2,f.GetReference(),ha='center',va='center',fontsize=6)
  # ROI 136..157, 104..119.5; 0.25 mm keepout around physical bounding boxes
  x0=max(0,int(np.floor((x-.25-136)*10)));x1=min(210,int(np.ceil((x+w+.25-136)*10)))
  y0=max(0,int(np.floor((y-.25-104)*10)));y1=min(155,int(np.ceil((y+h+.25-104)*10)))
  if x1>x0 and y1>y0:grid[y0:y1,x0:x1]=False
 heights=[0]*210;best=(0,0,0,0,0)
 for row in range(155):
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
with (v/'native-placement-changes.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['Reference','Old X mm','Old Y mm','Old native angle deg','New X mm','New Y mm','New native angle deg'])
 for x in c['moved']:w.writerow([x['ref']]+x['before']+x['after'])
hashes=json.loads((v/'baseline-hashes.json').read_text());prod={k:h for k,h in hashes.items() if k.startswith('production/')};assert all(hashlib.sha256((r/k).read_bytes()).hexdigest()==h for k,h in prod.items())
# Compare exported electrical connectivity, ignoring title/revision metadata.
def nets(path):
 root=E.parse(path).getroot();return {n.attrib['name']:sorted((q.attrib['ref'],q.attrib['pin']) for q in n.findall('node')) for n in root.findall('./nets/net')}
assert nets(v/'netlist.xml')==nets(r/'validation/thermal-20261020/netlist.xml')
print(json.dumps({'space':results,'production_files_unchanged':len(prod),'electrical_netlist_unchanged':True},indent=2))
