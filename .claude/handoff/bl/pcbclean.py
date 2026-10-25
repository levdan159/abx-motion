import pcbnew,re,sys,collections
SP='/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/'
sch=set(re.findall(r'\(comp\s+\(ref "([^"]*)"\)',open(SP+'n3.net').read()))
b=pcbnew.LoadBoard('abx-motion-brushless.kicad_pcb')
for f in [f for f in b.GetFootprints() if f.GetReference() not in sch]: b.Remove(f)
used={p.GetNetname() for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()}
tr=[t for t in b.GetTracks() if t.GetNetname() not in used]
c=collections.Counter(t.GetNetname() for t in tr)
for t in tr: b.Remove(t)
zs=[z for z in b.Zones() if z.GetNetname() not in used]
for z in zs: b.Remove(z)
print('removed tracks',len(tr),'nets',len(c),dict(c.most_common(12)),'zones',[(z.GetNetname(),z.GetLayerName()) for z in zs])
b.Save('abx-motion-brushless.kicad_pcb')
