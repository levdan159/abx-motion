import pcbnew,json,sys
b=pcbnew.LoadBoard(sys.argv[1]);xy=lambda p:[p.x,p.y]
fs={f.m_Uuid.AsString():dict(ref=f.GetReference(),value=f.GetValue(),fpid=str(f.GetFPID().GetLibNickname())+':'+str(f.GetFPID().GetLibItemName()),pos=xy(f.GetPosition()),rot=f.GetOrientationDegrees(),layer=f.GetLayer(),pads=sorted([dict(n=p.GetNumber(),net=p.GetNetname(),pos=xy(p.GetPosition()),size=xy(p.GetSize()),drill=xy(p.GetDrillSize())) for p in f.Pads()],key=lambda p:(p['n'],p['pos']))) for f in b.GetFootprints()}
ts={}
for t in b.GetTracks():
 q=dict(net=t.GetNetname(),kind=t.GetClass(),width=(t.GetWidth(pcbnew.F_Cu) if t.GetClass()=='PCB_VIA' else t.GetWidth()),layer=t.GetLayer())
 if t.GetClass()=='PCB_VIA':q.update(pos=xy(t.GetPosition()),drill=t.GetDrillValue(),top=t.TopLayer(),bottom=t.BottomLayer())
 else:q.update(start=xy(t.GetStart()),end=xy(t.GetEnd()))
 ts[t.m_Uuid.AsString()]=q
zs={z.m_Uuid.AsString():dict(net=z.GetNetname(),layers=z.GetLayerSet().FmtHex(),clear=z.GetLocalClearance().value() if hasattr(z.GetLocalClearance(),'value') else str(z.GetLocalClearance()),poly=str(z.Outline().Format())) for z in b.Zones()} if False else {}
print(json.dumps(dict(footprints=fs,copper=ts),indent=2))
