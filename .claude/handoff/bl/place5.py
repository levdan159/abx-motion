import pcbnew,math,re
P='/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b=pcbnew.LoadBoard(P); MM=1000000
def box(f):
    bb=f.GetBoundingBox(False,False); return [bb.GetX()/MM,bb.GetY()/MM,bb.GetRight()/MM,bb.GetBottom()/MM]
def hit(a,c,m=0.3): return not(a[2]+m<=c[0] or c[2]+m<=a[0] or a[3]+m<=c[1] or c[3]+m<=a[1])
def move(f,x,y,rot=0): f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(x*MM),int(y*MM)))
fp={f.GetReference():f for f in b.GetFootprints()}
# ---- fixed items first
def block(name_pred,REG,KEY,rail_skip,fallback,margin=0.3):
    mem=[f for f in b.GetFootprints() if name_pred(f)]; ms={f.GetReference() for f in mem}
    others=[box(f) for f in b.GetFootprints() if f.GetReference() not in ms]
    occ=[]; keys={}
    for r,(x,y,rot) in KEY.items(): move(fp[r],x,y,rot); occ.append(box(fp[r])); keys[r]=fp[r]
    def anchor(f):
        ref=f.GetReference(); nets=[p.GetNetname() for p in f.Pads()]; cand=[]
        for kr,k in keys.items():
            for p in k.Pads():
                n=p.GetNetname()
                if n in nets and n not in rail_skip:
                    cnt=sum(1 for ff in b.GetFootprints() for pp in ff.Pads() if pp.GetNetname()==n)
                    if cnt<=9: cand.append((cnt,0 if kr[0]=='U' else (1 if kr[0]=='Q' else 2),kr,p))
        if cand: cand.sort(key=lambda c:(c[0],c[1])); return keys[cand[0][2]],cand[0][3]
        return keys[fallback],None
    bad=[]
    for f in sorted([f for f in mem if f.GetReference() not in KEY],key=lambda f:(f.GetReference()[0] not in 'RC',f.GetReference())):
        a,pad=anchor(f); ac=a.GetPosition(); ax,ay=ac.x/MM,ac.y/MM
        if pad is not None:
            px,py=pad.GetX()/MM,pad.GetY()/MM; dx,dy=px-ax,py-ay; d=math.hypot(dx,dy) or 1; tx,ty=px+dx/d*2.0,py+dy/d*2.0
        else: tx,ty=ax,ay
        w=box(f); fw,fh=w[2]-w[0],w[3]-w[1]; done=False
        for r10 in range(0,300):
            r=r10*0.4
            for k in range(0,16 if r>0 else 1):
                ang=2*math.pi*k/16; x,y=tx+r*math.cos(ang),ty+r*math.sin(ang); bx=[x-fw/2,y-fh/2,x+fw/2,y+fh/2]
                if bx[0]<REG[0] or bx[2]>REG[2] or bx[1]<REG[1] or bx[3]>REG[3]: continue
                if any(hit(bx,o,margin) for o in occ) or any(hit(bx,o,margin) for o in others): continue
                move(f,x,y,0); occ.append(box(f)); done=True; break
            if done: break
        if not done: bad.append(f.GetReference())
    print('block',len(mem),'unplaced',bad)
def flip_back(f):
    if f.GetLayer()==pcbnew.F_Cu: f.Flip(f.GetPosition(),pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
for r,(x,y,rot) in {'H3':(50,161.5,0),'H4':(198,161.5,0),'J210':(80,160.5,0),'J211':(97,160.5,0),
  'J102':(196,82.1,90),'LOGO1':(60,154,0)}.items(): move(fp[r],x,y,rot)
flip_back(fp['LOGO2']); move(fp['LOGO2'],79.5,118,0)
PWR=lambda f: f.GetSheetname()=='/Power_Supply/' and f.GetReference() not in('H1','H2','H3','H4','LOGO1','LOGO2','J102','J1') and not f.GetReference().startswith('TP_')
block(PWR,(95.5,74.5,114.6,130),{'F1':(105,79,0),'Q1':(100,88,0),'D2':(109,88,0),'U1':(101,101,0),'L1':(110,101,0),'U2':(104,113,0)},{'GND','VBUS','+BATT','+3V3','+5V'},'U1')
BRK=lambda f: f.GetSheetname()=='/Brakes/'
block(BRK,(176.3,117.5,201.6,157.6),{'J501':(196,127.1,90),'J502':(196,140.1,90),
 'U502':(179.5,121.5,0),'Q501':(185,122.5,0),'D501':(185.5,128,0),'U503':(179.5,134.5,0),'Q502':(185,135.5,0),'D502':(185.5,141,0),
 'U501':(181,150,0),'L501':(191,150,0),'C503':(198.3,148,90),'C504':(198.3,154,90)},{'GND','+BATT','+3V3','VBUS'},'U501')
for d in b.GetDrawings():
    if d.GetLayerName()=='Edge.Cuts':
        s_,e=d.GetStart(),d.GetEnd()
        def f(v,old,new): return new if abs(v/MM-old)<0.2 else v/MM
        d.SetStart(pcbnew.VECTOR2I(int(s_.x),int(f(s_.y,204,166)*MM))); d.SetEnd(pcbnew.VECTOR2I(int(e.x),int(f(e.y,204,166)*MM)))
for z in list(b.Zones()): b.Remove(z)
b.Save(P)
bb=b.GetBoardEdgesBoundingBox(); print('outline',bb.GetX()/MM,bb.GetY()/MM,bb.GetRight()/MM,bb.GetBottom()/MM)
