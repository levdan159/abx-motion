import pcbnew
P='/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b=pcbnew.LoadBoard(P); MM=1000000
fp={f.GetReference():f for f in b.GetFootprints()}
def mv(r,dx=0,dy=0,x=None,y=None):
    f=fp[r]; f.SetPosition(pcbnew.VECTOR2I(int((x if x is not None else f.GetX()/MM+dx)*MM),int((y if y is not None else f.GetY()/MM+dy)*MM)))
mv('J308',dy=3); mv('J408',dy=3); mv('J102',x=191,y=80); mv('TP_GND2',x=198,y=66); mv('Y401',dy=-1.8)
for z in list(b.Zones()): b.Remove(z)
b.Save(P)
