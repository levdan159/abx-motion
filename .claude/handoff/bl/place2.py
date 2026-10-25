import pcbnew,math,re
P='/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b=pcbnew.LoadBoard(P); MM=1000000
def box(f):
    bb=f.GetBoundingBox(False,False); return [bb.GetX()/MM,bb.GetY()/MM,bb.GetRight()/MM,bb.GetBottom()/MM]
def hit(a,c,m=0.35): return not(a[2]+m<=c[0] or c[2]+m<=a[0] or a[3]+m<=c[1] or c[3]+m<=a[1])
def move(f,x,y,rot=0):
    f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(x*MM),int(y*MM)))
fp={f.GetReference():f for f in b.GetFootprints()}
# sensors headers to the bottom band
move(fp['J210'],95,159.5); move(fp['J211'],115,159.5)
# ---- Brakes block
REG=(118,104,203,162)
KEY={'U501':(126,114,0),'L501':(140,114,0),'C503':(152,111,0),'C504':(152,117,0),'C505':(122,125,0),'C506':(128,125,0),
 'U502':(130,138,0),'U503':(130,150,0),'Q501':(150,137,0),'Q502':(150,149,0),'D501':(162,137,0),'D502':(162,149,0),'J501':(184,137,0),'J502':(184,150,0)}
brk=[f for f in b.GetFootprints() if f.GetSheetname()=='/Brakes/']
bset={f.GetReference() for f in brk}
others=[box(f) for f in b.GetFootprints() if f.GetReference() not in bset]
occ=[]
for r,(x,y,rot) in KEY.items(): move(fp[r],x,y,rot); occ.append(box(fp[r]))
keys={r:fp[r] for r in KEY}
def anchor(f):
    nets=[p.GetNetname() for p in f.Pads()]; cand=[]
    for kr,k in keys.items():
        for p in k.Pads():
            n=p.GetNetname()
            if n in nets and n not in('GND','+BATT','+3V3'):
                cnt=sum(1 for ff in b.GetFootprints() for pp in ff.Pads() if pp.GetNetname()==n)
                if cnt<=9: cand.append((cnt,0 if kr[0]=='U' else 1,kr,p))
    if cand:
        cand.sort(key=lambda c:(c[0],c[1])); return keys[cand[0][2]],cand[0][3]
    return keys['U501'],None
for f in sorted([f for f in brk if f.GetReference() not in KEY],key=lambda f:f.GetReference()):
    a,pad=anchor(f); ac=a.GetPosition(); ax,ay=ac.x/MM,ac.y/MM
    if pad is not None:
        px,py=pad.GetX()/MM,pad.GetY()/MM; dx,dy=px-ax,py-ay; d=math.hypot(dx,dy) or 1; tx,ty=px+dx/d*2.2,py+dy/d*2.2
    else: tx,ty=ax,ay
    w=box(f); fw,fh=w[2]-w[0],w[3]-w[1]; done=False
    for r10 in range(0,200):
        r=r10*0.4
        for k in range(0,16 if r>0 else 1):
            ang=2*math.pi*k/16; x,y=tx+r*math.cos(ang),ty+r*math.sin(ang); bx=[x-fw/2,y-fh/2,x+fw/2,y+fh/2]
            if bx[0]<REG[0] or bx[2]>REG[2] or bx[1]<REG[1] or bx[3]>REG[3]: continue
            if any(hit(bx,o) for o in occ) or any(hit(bx,o) for o in others): continue
            move(f,x,y,0); occ.append(box(f)); done=True; break
        if done: break
    if not done: print('UNPLACED',f.GetReference())
b.Save(P); print('brakes placed',len(brk))
