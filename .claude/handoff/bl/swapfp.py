import pcbnew
P='/home/mark/Documents/abx-motion/abx-motion-brushless.kicad_pcb'
b=pcbnew.LoadBoard(P)
old=[f for f in b.GetFootprints() if f.GetReference() in('U302','U402')]
for o in old:
    n=pcbnew.FootprintLoad('/home/mark/Documents/abx-motion/abx-footprints.pretty','Texas_RTA0040B_WQFN-40-1EP_6x6mm_P0.5mm_EP4.15x4.15mm')
    n.SetPosition(o.GetPosition()); n.SetOrientation(o.GetOrientation())
    if o.IsFlipped(): n.Flip(o.GetPosition(),True)
    n.SetReference(o.GetReference()); n.SetValue(o.GetValue()); n.SetPath(o.GetPath())
    n.SetField('Datasheet',o.GetField('Datasheet') if hasattr(o,'GetField') else '') if False else None
    netmap={p.GetNumber():p.GetNet() for p in o.Pads() if p.GetNumber()}
    for p in n.Pads():
        if p.GetNumber() in netmap: p.SetNet(netmap[p.GetNumber()])
    n.SetLocked(o.IsLocked())
    b.Add(n); print('added',o.GetReference(),len(netmap),'pad nets')
for o in old: b.Remove(o)
b.Save(P)
