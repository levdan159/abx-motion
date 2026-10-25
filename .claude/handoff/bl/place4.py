import pcbnew,math,re
P='/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b=pcbnew.LoadBoard(P); MM=1000000
def box(f):
    bb=f.GetBoundingBox(False,False); return [bb.GetX()/MM,bb.GetY()/MM,bb.GetRight()/MM,bb.GetBottom()/MM]
def hit(a,c,m=0.3): return not(a[2]+m<=c[0] or c[2]+m<=a[0] or a[3]+m<=c[1] or c[3]+m<=a[1])
def move(f,x,y,rot=0): f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(int(x*MM),int(y*MM)))
fp={f.GetReference():f for f in b.GetFootprints()}
# ---- fixed items first
for r,(x,y,rot) in {'J1':(191,104,90),'J102':(191,72,0),'H3':(50,199,0),'H4':(198,199,0),'LOGO1':(191,130,0),'LOGO2':(191,146,0),
  'TP_BATT1':(183,60,0),'TP_5V1':(188,60,0),'TP_3V3_1':(193,60,0),'TP_GND1':(198,60,0),'TP_GND2':(198,65,0)}.items(): move(fp[r],x,y,rot)
move(fp['J210'],85,159.5); move(fp['J211'],104,159.5)
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
W,H=62,56
CHK={'C328':(7,9,0),'C329':(7,22,0),'Q301':(42,9,0),'Q302':(42,17.5,0),'Q303':(33,9,0),'Q304':(33,17.5,0),'Q305':(24,9,0),'Q306':(24,17.5,0),
 'R307':(42,25.5,0),'R308':(33,25.5,0),'R309':(24,25.5,0),'J301':(55.5,8,90),'J302':(55.5,15,90),'J303':(55.5,22,90),
 'U302':(27,37,0),'U301':(11,39,0),'U303':(40,33,0),'U304':(49,38,0),'U305':(44,44,0),
 'J304':(13.5,52,0),'J305':(29.5,52,0),'J306':(47,52,0),'J307':(58.5,38,0),'J308':(58.5,50,0)}
for i,x in enumerate(range(0,7)): CHK['C%d'%(321+i)]=(21.6+5.2*i,3,0)
def sh(r,off): return re.sub(r'(\d{3})$',lambda m:str(int(m.group(1))+off),r)
for ch,(ox,oy,pre,off) in {1:(115,48,'/68e0475f',0),2:(115,106,'/df9be12f',100)}.items():
    KEY={sh(r,off):(ox+x,oy+y,rot) for r,(x,y,rot) in CHK.items()}
    block(lambda f,pre=pre:f.GetPath().AsString().startswith(pre),(ox+0.5,oy+0.5,ox+W-0.5,oy+H-0.5),KEY,{'GND','VBUS'},sh('U301',off))
PWR=lambda f: f.GetSheetname()=='/Power_Supply/' and f.GetReference() not in('H1','H2','H3','H4','LOGO1','LOGO2','J102','J1') and not f.GetReference().startswith('TP_')
block(PWR,(53,164,121,203),{'F1':(66,170,0),'Q1':(84,170,0),'D2':(101,171,0),'U1':(80,186,0),'L1':(94,187,0),'U2':(110,186,0)},{'GND','VBUS','+BATT','+3V3','+5V'},'U1')
BRK=lambda f: f.GetSheetname()=='/Brakes/'
block(BRK,(122,164,196,203),{'U501':(128,170,0),'L501':(142,170,0),'C503':(154,167,0),'C504':(154,173,0),'C505':(126,180,0),'C506':(132,180,0),
 'U502':(130,190,0),'Q501':(148,188,0),'D501':(160,188,0),'U503':(130,198,0),'Q502':(148,198,0),'D502':(160,198,0),'J501':(186,174,0),'J502':(186,190,0)},{'GND','+BATT','+3V3'},'U501')
# outline + zones
for d in b.GetDrawings():
    if d.GetLayerName()=='Edge.Cuts':
        s,e=d.GetStart(),d.GetEnd()
        def f(v,old,new): return new if abs(v/MM-old)<0.2 else v/MM
        d.SetStart(pcbnew.VECTOR2I(int(f(s.x,277,202)*MM),int(f(s.y,165,204)*MM))); d.SetEnd(pcbnew.VECTOR2I(int(f(e.x,277,202)*MM),int(f(e.y,165,204)*MM)))
b.Save(P)
bb=b.GetBoardEdgesBoundingBox(); print('outline',bb.GetX()/MM,bb.GetY()/MM,bb.GetRight()/MM,bb.GetBottom()/MM)
