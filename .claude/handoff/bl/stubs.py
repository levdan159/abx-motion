import pcbnew
SP='/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/'
old=pcbnew.LoadBoard(SP+'pcb_pre_orphan.kicad_pcb')
pads=[]
for r in ['R204','R205','R207','R208','R209','R210','R621','R622']:
    f=old.FindFootprintByReference(r)
    pads+= [(p.GetX(),p.GetY(),p.GetLayer()) for p in f.Pads()]
b=pcbnew.LoadBoard('abx-motion-brushless.kicad_pcb')
def near(x,y,px,py,tol=300000): return abs(x-px)<=tol and abs(y-py)<=tol
removed=0
for it in range(20):
    tr=[t for t in b.GetTracks()]
    ends={}
    pts=[]
    for f in b.GetFootprints():
        for p in f.Pads(): pts.append((p.GetX(),p.GetY(),'pad',p.GetLayerSet()))
    vias=[(t.GetX(),t.GetY()) for t in tr if t.GetClass()=='PCB_VIA']
    segs=[t for t in tr if t.GetClass()=='PCB_TRACK']
    dead=[]
    for s in segs:
        for e,o in ((s.GetStart(),s.GetEnd()),(s.GetEnd(),s.GetStart())):
            if not any(near(e.x,e.y,px,py) for px,py,_ in pads) and not any(near(e.x,e.y,*[q for q in (0,0)]) for q in []): 
                pass
        # candidate if either end near a removed pad
        cand=any(near(e.x,e.y,px,py) for e in (s.GetStart(),s.GetEnd()) for px,py,_ in pads)
        if not cand: continue
        for e in (s.GetStart(),s.GetEnd()):
            if any(near(e.x,e.y,px,py,10000) for px,py,_,_ in pts): continue
            if any(near(e.x,e.y,vx,vy,10000) for vx,vy in vias): continue
            if any(o is not s and any(near(e.x,e.y,q.x,q.y,10000) for q in (o.GetStart(),o.GetEnd())) for o in segs): continue
            dead.append(s); break
    if not dead: break
    for s in dead: b.Remove(s)
    removed+=len(dead); 
    pads+= [(q.x,q.y,0) for s in dead for q in (s.GetStart(),s.GetEnd())]
print('stub tracks removed',removed)
b.Save('abx-motion-brushless.kicad_pcb')
