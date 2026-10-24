from pathlib import Path
import pcbnew,json,sys
R=Path.cwd();sys.path.insert(0,str(R/'work/rev-1.2-completion/phase2/interlock'));from router_defs import Router
b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));r=Router(b);net='/M1_PWM_PH';path=None
for y in [60.,59.9,59.8,59.7,59.6,59.5,59.4]:
 candidate=[(96.9,60.5),(96.9,y),(101.8,y),(102.8,y+1),(102.8,62.6)]
 if all(r.seg_clear(net,1,*a,*z,.075,.15) for a,z in zip(candidate,candidate[1:])):path=candidate;break
assert path,'No local TIM bypass clearance'
hold=[t for t in b.GetTracks() if t.m_Uuid.AsString() in ['4bce76bb-1330-45df-b1d9-5e2606d70df8','27b9a183-bf20-4f48-a09e-044e9f457b07']]
assert len(hold)==2
for t in hold:b.Remove(t)
for a,z in zip(path,path[1:]):
 t=pcbnew.PCB_TRACK(b);t.SetStart(pcbnew.VECTOR2I(round(a[0]*1e6),round(a[1]*1e6)));t.SetEnd(pcbnew.VECTOR2I(round(z[0]*1e6),round(z[1]*1e6)));t.SetLayer(pcbnew.B_Cu);t.SetWidth(150000);t.SetNetCode(b.FindNet(net).GetNetCode());b.Add(t)
zero=[t for t in b.GetTracks() if t.GetClass()=='PCB_TRACK' and t.GetStart()==t.GetEnd()]
for t in zero:b.Remove(t)
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(R/'abx-motion.kicad_pcb'),b)
(R/'work/drc-cleanup-20261024/tim-bypass.json').write_text(json.dumps(dict(net=net,path=path,zero_length_tracks_removed=len(zero)),indent=2)+'\n');print('Bypassed TIM pad',path,'removed',len(zero),'zero-length tracks')
