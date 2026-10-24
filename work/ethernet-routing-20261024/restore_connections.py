from pathlib import Path
import ast,sys,json,math,struct,subprocess,shutil,hashlib,time
import numpy as np
import pcbnew
ROOT=Path.cwd();OUT=ROOT/'work/ethernet-routing-20261024';P=ROOT/'variants/ABX-Motion-ETH'
sys.path.insert(0,str(ROOT/'work/rev-1.2-completion/phase2/interlock'))
from router_defs import Router
class NativeRouter(Router):
 def seg_clear(self,net,lid,x1,y1,x2,y2,half_w=.1,clr=.15):return super().seg_clear(net,lid,x1,y1,x2,y2,half_w,clr)
 def via_clear(self,net,x,y,via_r=.25,clr=.15):return super().via_clear(net,x,y,via_r,clr)
b=pcbnew.LoadBoard(str(P/'abx-motion-eth-placement.kicad_pcb'));pcbnew.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();r=NativeRouter(b)
r.reserves=[]
route_reserves=[(111.06,48,130.06,62.0),(117,79.8,122,84.5),(132.6,53.3,158.5,59.35)]
xy=lambda o:tuple(pcbnew.ToMM(v) for v in (o.GetPosition().x,o.GetPosition().y))
tree=ast.parse((ROOT/'work/rev-1.2-electrical/control-rework-20261022/astar_fine.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['component','anchors']],type_ignores=[]),'defs','exec'),globals())
X0,Y0,G=45.,48.,.1;W,H=1571,1051;N=W*H
# Rasterize exact distance fields in small local windows; new copper is checked again using exact geometry.
def masks(net,w):
 m=np.zeros((3,H,W),dtype=np.uint8);v=np.zeros((H,W),dtype=np.uint8)
 def paint(arr,bb,rad,shape,coords):
  x1,y1,x2,y2=bb;lo=max(0,math.floor((x1-rad-X0)/G));hi=min(W,math.ceil((x2+rad-X0)/G)+1);bot=max(0,math.floor((y1-rad-Y0)/G));top=min(H,math.ceil((y2+rad-Y0)/G)+1)
  if lo>=hi or bot>=top:return
  xx=X0+np.arange(lo,hi)[None,:]*G;yy=Y0+np.arange(bot,top)[:,None]*G
  if shape=='rect':
   a,c,z,t=coords;dist=np.maximum(a-xx,np.maximum(0,xx-z))**2+np.maximum(c-yy,np.maximum(0,yy-t))**2
  else:
   a,c,z,t=coords;dx=z-a;dy=t-c;fac=np.clip(((xx-a)*dx+(yy-c)*dy)/(dx*dx+dy*dy or 1),0,1);dist=(xx-a-fac*dx)**2+(yy-c-fac*dy)**2
  arr[bot:top,lo:hi]|=(dist<(rad-1e-6)**2).astype(np.uint8)
 obs=set(q for vals in r.idx.values() for q in vals)
 for typ,q in obs:
  same=q[0]==net
  if typ=='p':
   bb=q[2:6]
   if not same:
    for l in range(3):
     if q[1]&(1<<l):paint(m[l],bb,w/2+.17,'rect',bb)
   if q[1]:paint(v,bb,(.5 if q[6] else .15) if same else (.5 if q[6] else .43),'rect',bb)
  elif typ=='v':
   _,x,y,rad=q;bb=(x,y,x,y);coords=bb
   if not same:
    for l in range(3):paint(m[l],bb,w/2+.17+rad,'seg',coords)
   paint(v,bb,max(.25+rad+(.25 if same else .15),.5),'seg',coords)
  elif not same:
   _,l,x,y,z,t,rad,*_=q;bb=(min(x,z),min(y,t),max(x,z),max(y,t));paint(m[l],bb,w/2+.17+rad,'seg',(x,y,z,t));paint(v,bb,.43+rad,'seg',(x,y,z,t))
 for rr in route_reserves:
  for l in range(3):paint(m[l],rr,w/2+.17,'rect',rr)
  paint(v,rr,.4,'rect',rr)
 for tim in [(97.5,60.46,101.5,64.46),(133.5,78.8,136.7,81.4),(84.2,115.45,91.8,132.05),(104.2,115.45,111.8,132.05),(124.2,115.45,131.8,132.05)]:
  paint(m[1],tim,w/2+.25,'rect',tim);paint(v,tim,.55,'rect',tim)
 mdi=(115,67.8,125.5,70.7);paint(m[0],mdi,w/2+.17,'rect',mdi);paint(v,mdi,.4,'rect',mdi)
 for nn,x,y,rad in r.vias:
  if nn==net:
   gx,gy=round((x-X0)/G),round((y-Y0)/G)
   if 0<=gx<W and 0<=gy<H and math.dist((x,y),(X0+gx*G,Y0+gy*G))<1e-6:v[gy,gx]=0
 return m,v

def run(a,z):
 net=a.GetNetname();w=.4 if net in ['+3V3','+5V','+BATT'] else .3 if net=='GND' else .15
 aa,zz=anchors(component(a),net,w),anchors(component(z),net,w)
 m,v=masks(net,w)
 def convert(an):
  d={}
  for (x,y,l),end in an.items():
   xx=x-round(X0*10);yy=y-round(Y0*10)
   if any(a-.2<=x/10<=c+.2 and bb-.2<=y/10<=dd+.2 for a,bb,c,dd in route_reserves):continue
   if l==0 and 115<=x/10<=125.5 and 67.8<=y/10<=70.7:continue
   if 0<=xx<W and 0<=yy<H:d[(xx,yy,l)]=end
  return d
 aa,zz=convert(aa),convert(zz)
 # Existing connection anchors can occupy a conservatively inflated pixel, but must still be exact-clear.
 for an in [aa,zz]:
  for (x,y,l),end in list(an.items()):
   if not r.seg_clear(net,l,X0+x*G,Y0+y*G,X0+x*G,Y0+y*G,w/2):del an[(x,y,l)]
   else:m[l,y,x]=0
 def ids(an):return np.array([l*N+y*W+x for x,y,l in an],dtype=np.int32)
 av,zv=ids(aa),ids(zz)
 print('Grid',net,len(av),len(zv),flush=True)
 with open(OUT/'grid.bin','wb') as f:
  f.write(struct.pack('ii',W,H));f.write(m.tobytes());f.write(v.tobytes());f.write(struct.pack('i',len(av)));f.write(av.tobytes());f.write(struct.pack('i',len(zv)));f.write(zv.tobytes())
 try:done=subprocess.run(['/tmp/abx-eth-grid',str(OUT/'grid.bin'),str(OUT/'grid-path.json')],timeout=25)
 except subprocess.TimeoutExpired:print('Bounded search timed out',net,flush=True);return False
 path=json.loads((OUT/'grid-path.json').read_text())
 if not path:print('No grid path',net,flush=True);return False
 path=[(round(X0+x*G,6),round(Y0+y*G,6),l) for x,y,l in path]
 # Compress collinear steps, then check every full segment before modifying board.
 compact=[path[0]]
 for i in range(1,len(path)-1):
  a0,p,z0=path[i-1:i+2]
  if (p[2]!=a0[2] or p[2]!=z0[2] or (p[0]-a0[0])*(z0[1]-p[1])-(p[1]-a0[1])*(z0[0]-p[0])>1e-7 or abs((p[0]-a0[0])*(z0[1]-p[1])-(p[1]-a0[1])*(z0[0]-p[0]))>1e-7):compact.append(p)
 compact.append(path[-1])
 for a0,z0 in zip(compact,compact[1:]):
  if a0[2]==z0[2]:assert r.seg_clear(net,a0[2],*a0[:2],*z0[:2],w/2),(net,a0,z0)
  else:
   exists=any(nn==net and math.dist((x,y),a0[:2])<1e-6 for nn,x,y,rad in r.vias)
   assert exists or r.via_clear(net,*a0[:2]),('via',a0)
 for p0,an in [(path[0],aa),(path[-1],zz)]:
  x,y,l=p0;end=an[(round((x-X0)/G),round((y-Y0)/G),l)];r.add_seg(net,l,*end[:2],x,y,w)
 for a0,z0 in zip(compact,compact[1:]):
  if a0[2]==z0[2]:r.add_seg(net,a0[2],*a0[:2],*z0[:2],w)
  elif not any(nn==net and math.dist((x,y),a0[:2])<1e-6 for nn,x,y,rad in r.vias):r.add_via(net,*a0[:2])
 b.BuildConnectivity();print('Added',net,len(compact),'vertices',flush=True);return True



report=json.loads((OUT/sys.argv[1]).read_text());objects={t.m_Uuid.AsString():t for t in b.GetTracks()}
for f in b.GetFootprints():
 for pad in f.Pads():objects[pad.m_Uuid.AsString()]=pad
results=[];before={t.m_Uuid.AsString() for t in b.GetTracks()}
links=sorted(report['unconnected_items'],key=lambda q:math.dist(tuple(q['items'][0]['pos'].values()),tuple(q['items'][1]['pos'].values())))
for link in links:
 a,z=[objects.get(q['uuid']) for q in link['items']]
 if a is None or z is None or a.GetNetname().startswith('unconnected-'):continue
 if any(vv.m_Uuid.AsString()==z.m_Uuid.AsString() for vv in component(a)):continue
 started=time.monotonic()
 try:ok=run(a,z)
 except AssertionError as err:print('Candidate rejected:',str(err),flush=True);ok=False
 results.append(dict(net=a.GetNetname(),success=ok,seconds=round(time.monotonic()-started,2)))
 pcbnew.SaveBoard(str(OUT/'restoration-progress.kicad_pcb'),b)
 (OUT/('restoration-'+sys.argv[2]+'.json')).write_text(json.dumps(results,indent=2)+'\n')
pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(OUT/'restoration-progress.kicad_pcb'),b)
shutil.copy2(OUT/'restoration-progress.kicad_pcb',P/'abx-motion-eth-placement.kicad_pcb')
added=[dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),kind=t.GetClass()) for t in b.GetTracks() if t.m_Uuid.AsString() not in before]
(OUT/('restoration-added-'+sys.argv[2]+'.json')).write_text(json.dumps(added,indent=2)+'\n')
print('RESTORATION PASS COMPLETE',len(results),'attempts',sum(q['success'] for q in results),'connected',len(added),'objects added',flush=True)
