from pathlib import Path
import pcbnew as p,json
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));tracks=list(b.GetTracks());t=next(t for t in tracks if t.m_Uuid.AsString()=='7552587b-a79e-4f63-8452-de6e79f4c456');a=t.GetStart();z=t.GetEnd();print('Local BTN_BACK detour',p.ToMM(a.x),p.ToMM(a.y),p.ToMM(z.x),p.ToMM(z.y));assert abs(p.ToMM(a.y)-149.3)<.00001 and abs(p.ToMM(z.y)-149.3)<.00001
left,right=sorted([(p.ToMM(a.x),p.ToMM(a.y)),(p.ToMM(z.x),p.ToMM(z.y))]);pts=[left,(96.3,149.3),(97.2,150.2),(98.6,150.2),(99.5,149.3),right];new=[]
for k,(a,z) in enumerate(zip(pts,pts[1:])):
 q=t if k==0 else p.PCB_TRACK(b)
 q.SetStart(p.VECTOR2I(p.FromMM(a[0]),p.FromMM(a[1])));q.SetEnd(p.VECTOR2I(p.FromMM(z[0]),p.FromMM(z[1])));q.SetLayer(p.B_Cu);q.SetWidth(t.GetWidth());q.SetNet(t.GetNet())
 if k:b.Add(q);new.append(q.m_Uuid.AsString())
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'local-detour.json').write_text(json.dumps({'modified_track_uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'new_tracks':new,'points_mm':pts},indent=2))
