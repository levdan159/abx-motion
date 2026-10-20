from pathlib import Path
import math, json
import pcbnew as p
OUT = Path(__file__).resolve().parent
b = p.LoadBoard(str(OUT/'before/abx-motion.kicad_pcb'))
pt = lambda x,y: p.VECTOR2I(p.FromMM(x),p.FromMM(y))
xy = lambda v: (p.ToMM(v.x),p.ToMM(v.y))
obs = {}
for layer in [p.F_Cu,p.B_Cu,p.In1_Cu,p.In2_Cu]:
    rows=[]
    for f in b.GetFootprints():
        for q in f.Pads():
            if q.IsOnLayer(layer): rows.append((q.GetNetname(),q.GetEffectiveShape(layer)))
    for t in b.GetTracks():
        if t.IsOnLayer(layer): rows.append((t.GetNetname(),t.GetEffectiveShape(layer)))
    obs[layer]=rows
def clear(shape,net,layer,margin=.2):
    return not any(n!=net and p.SHAPE.Collide(shape,s,p.FromMM(margin)) for n,s in obs[layer])
def line(a,z):return p.SHAPE_SEGMENT(pt(*a),pt(*z),p.FromMM(.22))
def path_clear(points,net,layer):return all(clear(line(a,z),net,layer) for a,z in zip(points,points[1:]) if a!=z)
def via_clear(v,net):
    shape=p.SHAPE_CIRCLE(pt(*v),p.FromMM(.3))
    return all(clear(shape,net,l,.25) for l in obs)
f=p.FootprintLoad('/usr/share/kicad/footprints/Resistor_SMD.pretty','R_0603_1608Metric')
existing=[]
for old in b.GetFootprints():
    old.BuildCourtyardCaches()
    c=old.GetCourtyard(p.F_Cu)
    if c.OutlineCount():existing.append(c)
found={}
for ref,net,target in [('R313','/M1_CS',(171.,86.)),('R413','/M2_CS',(157.5,101.5))]:
    sites=sorted([(target[0]+i*.5,target[1]+j*.5,angle) for i in range(-9,10)
                  for j in range(-9,10) for angle in [0,90,180,270]],
                 key=lambda v:(v[0]-target[0])**2+(v[1]-target[1])**2)
    for x,y,angle in sites:
        f.SetPosition(pt(x,y));f.SetOrientationDegrees(angle);f.BuildCourtyardCaches()
        court=f.GetCourtyard(p.F_Cu)
        if any(court.Collide(c,0) for c in existing):continue
        pads={q.GetNumber():q for q in f.Pads()}
        if not clear(pads['1'].GetEffectiveShape(p.F_Cu),net,p.F_Cu):continue
        if not clear(pads['2'].GetEffectiveShape(p.F_Cu),'GND',p.F_Cu):continue
        a=xy(pads['1'].GetPosition());z=xy(pads['2'].GetPosition())
        dx=(a[0]-x)/.825;dy=(a[1]-y)/.825
        v=(a[0]+dx*1.0,a[1]+dy*1.0);g=(z[0]-dx*1.0,z[1]-dy*1.0)
        if not via_clear(v,net) or not via_clear(g,'GND'):continue
        if not path_clear([a,v],net,p.F_Cu) or not path_clear([z,g],'GND',p.F_Cu):continue
        dx,dy=target[0]-v[0],target[1]-v[1]
        d=min(abs(dx),abs(dy))
        bend=(v[0]+math.copysign(d,dx),v[1]+math.copysign(d,dy))
        paths=[[v,bend,target],[v,(v[0],target[1]),target],[v,(target[0],v[1]),target],[v,target]]
        good=next((points for points in paths if path_clear(points,net,p.B_Cu)),None)
        if good is None:continue
        found[ref]={'xy':[x,y],'angle':angle,'signal_pad':a,'ground_pad':z,
                    'signal_via':v,'ground_via':g,'B_Cu_path':good}
        print(ref,found[ref],flush=True);break
    assert ref in found, ref
(OUT/'local-sites.json').write_text(json.dumps(found,indent=2)+'\n')
