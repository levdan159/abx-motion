import pcbnew,collections
b=pcbnew.LoadBoard('abx-motion-brushless.kicad_pcb')
used={p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()}
tr=[t for t in b.GetTracks() if t.GetNetname() not in used]
c=collections.Counter(t.GetNetname() for t in tr)
zs=[(z.GetNetname(),z.GetLayerName()) for z in b.Zones() if z.GetNetname() not in used]
for t in tr: b.Remove(t)
for z in [z for z in b.Zones() if z.GetNetname() not in used]: b.Remove(z)
b.Save('abx-motion-brushless.kicad_pcb')
print('tracks',len(tr),dict(c.most_common(15)),'zones',zs)
