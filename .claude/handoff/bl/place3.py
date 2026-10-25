import pcbnew,math
P='/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b=pcbnew.LoadBoard(P); MM=1000000
def box(f):
    bb=f.GetBoundingBox(False,False); return [bb.GetX()/MM,bb.GetY()/MM,bb.GetRight()/MM,bb.GetBottom()/MM]
def hit(a,c,m=0.35): return not(a[2]+m<=c[0] or c[2]+m<=a[0] or a[3]+m<=c[1] or c[3]+m<=a[1])
def move(f,x,y,rot=0): f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(x*MM),int(y*MM)))
fp={f.GetReference():f for f in b.GetFootprints()}
move(fp['J210'],85,159.5); move(fp['J211'],104,159.5)
def block(name_pred,REG,KEY,rail_skip,fallback):
    mem=[f for f in b.GetFootprints() if name_pred(f)]; ms={f.GetReference() for f in mem}
    others=[box(f) for f in b.GetFootprints() if f.GetReference() not in ms]
    occ=[]; keys={}
    for r,(x,y,rot) in KEY.items(): move(fp[r],x,y,rot); occ.append(box(fp[r])); keys[r]=fp[r]
    def anchor(f):
        nets=[p.GetNetname() for p in f.Pads()]; cand=[]
        for kr,k in keys.items():
            for p in k.Pads():
                n=p.GetNetname()
                if n in nets and n not in rail_skip:
                    cnt=sum(1 for ff in b.GetFootprints() for pp in ff.Pads() if pp.GetNetname()==n)
                    if cnt<=9: cand.append((cnt,0 if kr[0]=='U' else 1,kr,p))
        if cand: cand.sort(key=lambda c:(c[0],c[1])); return keys[cand[0][2]],cand[0][3]
        return keys[fallback],None
    bad=[]
    for f in sorted([f for f in mem if f.GetReference() not in KEY],key=lambda f:f.GetReference()):
        a,pad=anchor(f); ac=a.GetPosition(); ax,ay=ac.x/MM,ac.y/MM
        if pad is not None:
            px,py=pad.GetX()/MM,pad.GetY()/MM; dx,dy=px-ax,py-ay; d=math.hypot(dx,dy) or 1; tx,ty=px+dx/d*2.2,py+dy/d*2.2
        else: tx,ty=ax,ay
        w=box(f); fw,fh=w[2]-w[0],w[3]-w[1]; done=False
        for r10 in range(0,250):
            r=r10*0.4
            for k in range(0,16 if r>0 else 1):
                ang=2*math.pi*k/16; x,y=tx+r*math.cos(ang),ty+r*math.sin(ang); bx=[x-fw/2,y-fh/2,x+fw/2,y+fh/2]
                if bx[0]<REG[0] or bx[2]>REG[2] or bx[1]<REG[1] or bx[3]>REG[3]: continue
                if any(hit(bx,o) for o in occ) or any(hit(bx,o) for o in others): continue
                move(f,x,y,0); occ.append(box(f)); done=True; break
            if done: break
        if not done: bad.append(f.GetReference())
    print('block',len(mem),'unplaced',bad)
PWR=lambda f: f.GetSheetname()=='/Power_Supply/' and f.GetReference() not in('H1','H2','H3','H4','LOGO1','LOGO2','J102') and not f.GetReference().startswith('TP_')
block(PWR,(118,86,186,122),{'J1':(195,106,90),'F1':(172,90,0),'D2':(175,100,0),'Q1':(160,100,0),'U1':(140,100,0),'L1':(150,110,0),'U2':(128,92,0)},{'GND','VBUS','+BATT','+3V3','+5V'},'U1')
BRK=lambda f: f.GetSheetname()=='/Brakes/'
block(BRK,(118,124,203,162),{'U501':(125,130,0),'L501':(139,130,0),'C503':(150,127,0),'C504':(150,133,0),'C505':(122,140,0),'C506':(128,140,0),
 'U502':(125,150,0),'Q501':(145,148,0),'D501':(158,148,0),'U503':(125,157,0),'Q502':(145,157,0),'D502':(158,157,0),'J501':(184,135,0),'J502':(184,152,0)},{'GND','+BATT','+3V3'},'U501')
b.Save(P)
