import pcbnew,sys
P='/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b=pcbnew.LoadBoard(P); MM=1e6
def box(f):
    bb=f.GetBoundingBox(False,False); return (bb.GetX()/MM,bb.GetY()/MM,bb.GetRight()/MM,bb.GetBottom()/MM)
g={}
for f in b.GetFootprints():
    s=f.GetSheetname(); r=f.GetReference()
    if r.startswith(('3','4')): pass
    key=s if not s.startswith('/ESC') else s
    g.setdefault(key,[]).append((r,box(f),f.GetValue(),f.GetFPID().GetLibItemName().wx_str()))
for k,v in sorted(g.items()):
    xs=[a[1] for a in v]; print('==',k,len(v),'bbox %.1f %.1f %.1f %.1f'%(min(x[0] for x in xs),min(x[1] for x in xs),max(x[2] for x in xs),max(x[3] for x in xs)))
    if len(sys.argv)>1 and any(s in k for s in sys.argv[1:]):
        for r,bx,val,fpn in sorted(v): print('  %-9s %6.1f %6.1f %6.1f %6.1f  %5.1fx%-5.1f %s %s'%(r,*bx,bx[2]-bx[0],bx[3]-bx[1],val,fpn[:40]))
