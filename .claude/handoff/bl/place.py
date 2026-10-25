import pcbnew,math,re,sys
P='/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b=pcbnew.LoadBoard(P)
MM=1000000
W,H=70.0,58.0                       # channel block, mm
CH={1:(205.0,48.0,'/68e0475f',0),2:(205.0,106.0,'/df9be12f',100)}
# key parts: ref number (ch1 numbering) -> (x, y, rot) local mm
KEY={
 'C328':(7,9,0),'C329':(7,23,0),
 'Q301':(42,9,0),'Q302':(42,17.5,0),'Q303':(32,9,0),'Q304':(32,17.5,0),'Q305':(22,9,0),'Q306':(22,17.5,0),
 'R307':(42,26,0),'R308':(32,26,0),'R309':(22,26,0),
 'J301':(63,7,90),'J302':(63,14,90),'J303':(63,21,90),
 'U302':(34,40,0),'U301':(12,46,0),'U303':(46,35,0),'U304':(54,44,0),'U305':(52,49.5,0),
 'J304':(24,55.5,0),'J305':(40,55.5,0),'J306':(55,55.5,0),'J307':(66,39,0),'J308':(66,53,0),
}
for i,x in enumerate((18,23.2,28.4,33.6,38.8,44,49.2)): KEY['C%d'%(321+i)]=(x,3.2,0)
GATE={'R310':'Q301','R311':'Q302','R312':'Q303','R313':'Q304','R314':'Q305','R315':'Q306'}
def num(ref): return ref
def sh(ref,off): return re.sub(r'(\d{3})$',lambda m:str(int(m.group(1))+off),ref)
def box(f):
    bb=f.GetBoundingBox(False,False); return [bb.GetX()/MM,bb.GetY()/MM,bb.GetRight()/MM,bb.GetBottom()/MM]
def hit(a,c,m=0.35): return not(a[2]+m<=c[0] or c[2]+m<=a[0] or a[3]+m<=c[1] or c[3]+m<=a[1])
def move(f,x,y,rot):
    f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(x*MM),int(y*MM)))
def place(ch):
    ox,oy,pre,off=CH[ch]
    fp={f.GetReference():f for f in b.GetFootprints() if f.GetPath().AsString().startswith(pre)}
    occ=[]; keys={}
    for r,(x,y,rot) in KEY.items():
        f=fp[sh(r,off)]; move(f,ox+x,oy+y,rot); keys[f.GetReference()]=f; occ.append(box(f))
    placed=set(keys)
    rest=[f for r,f in fp.items() if r not in placed]
    def anchor(f):
        ref=f.GetReference(); base=sh(ref,-off) if off else ref
        if base in GATE: 
            q=fp[sh(GATE[base],off)]; gnet=[p.GetNetname() for p in f.Pads()]
            for p in q.Pads():
                if p.GetNetname() in gnet and p.GetNetname()!=q.Pads()[0].GetNetname() and p.GetNumber()=='4': return q,p
            return q,None
        nets=[p.GetNetname() for p in f.Pads()]
        cand=[]
        for kr,k in keys.items():
            for p in k.Pads():
                n=p.GetNetname()
                if n in nets and n!='GND' and n!='VBUS':
                    cnt=sum(1 for ff in fp.values() for pp in ff.Pads() if pp.GetNetname()==n)
                    cand.append((cnt,0 if kr[0]=='U' else 1,kr,p))
        cand=[c for c in cand if c[0]<=9]
        if cand:
            cand.sort(key=lambda c:(c[0],c[1])); c=cand[0]; return keys[c[2]],c[3]
        return keys[sh('U301',off)],None
    items=sorted(rest,key=lambda f:(f.GetReference()[0]!='R' and f.GetReference()[0]!='C',f.GetReference()))
    for f in items:
        a,pad=anchor(f)
        ac=a.GetPosition(); ax,ay=ac.x/MM,ac.y/MM
        if pad is not None:
            px,py=pad.GetX()/MM,pad.GetY()/MM; dx,dy=px-ax,py-ay; d=math.hypot(dx,dy) or 1
            tx,ty=px+dx/d*2.2,py+dy/d*2.2
        else: tx,ty=ax,ay
        w=box(f); fw,fh=w[2]-w[0],w[3]-w[1]
        done=False
        for r10 in range(0,200):
            r=r10*0.4
            for k in range(0,16 if r>0 else 1):
                ang=2*math.pi*k/16
                x,y=tx+r*math.cos(ang),ty+r*math.sin(ang)
                bx=[x-fw/2,y-fh/2,x+fw/2,y+fh/2]
                if bx[0]<ox+0.5 or bx[2]>ox+W-0.5 or bx[1]<oy+0.5 or bx[3]>oy+H-0.5: continue
                if any(hit(bx,o) for o in occ): continue
                move(f,x,y,0); occ.append(box(f)); done=True; break
            if done: break
        if not done: print('UNPLACED',f.GetReference())
    print('channel',ch,'placed',len(fp))
for ch in (1,2): place(ch)
def free_spot(f,nx,ny):
    others=[box(o) for o in b.GetFootprints() if o is not f and o.GetReference()!=f.GetReference()]
    w=box(f); fw,fh=w[2]-w[0],w[3]-w[1]
    for r10 in range(0,400):
        r=r10*0.5
        for k in range(0,24 if r>0 else 1):
            a=2*math.pi*k/24; x,y=nx+r*math.cos(a),ny+r*math.sin(a)
            bx=[x-fw/2,y-fh/2,x+fw/2,y+fh/2]
            if bx[0]<47 or bx[2]>200 or bx[1]<50 or bx[3]>151: continue
            if any(hit(bx,o,1.0) for o in others): continue
            move(f,x,y,0); return x,y
for r,(x,y) in {'U4':(62,140),'J210':(118,140),'J211':(140,140)}.items():
    f=b.FindFootprintByReference(r); print(r,free_spot(f,x,y))
b.Save(P)
