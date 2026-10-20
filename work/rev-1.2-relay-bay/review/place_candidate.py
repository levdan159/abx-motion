from pathlib import Path
import pcbnew as p,json,shutil
O=Path(__file__).resolve().parent;P=O.parent
ROOT=P.parents[1]
shutil.copy2(O/'before.kicad_pcb',P/'abx-motion.kicad_pcb')
shutil.copy2(ROOT/'abx-motion.kicad_pro',P/'abx-motion.kicad_pro')
b=p.LoadBoard(str(P/'abx-motion.kicad_pcb'))
placements={'K501': (144.5, 122, 0), 'K502': (173.6, 133.5, 270), 'R207': (149, 114.1, 0), 'R501': (145, 114.1, 0), 'R502': (149, 116.8, 0), 'D502': (153, 116.8, 0), 'Q501': (140, 117.2, 0), 'D501': (145, 116.6, 0), 'R503': (163.5, 121, 0), 'R208': (163.5, 123, 0), 'R504': (159.5, 118.5, 0), 'D504': (163, 118.5, 0), 'Q502': (168.5, 121.5, 0), 'D503': (172.6, 122, 0)}
private={q.GetNetname() for f in b.GetFootprints() for q in f.Pads() if '/Steppers_and_Relays/RLY' in q.GetNetname()};removed=[]
original_tracks=list(b.GetTracks());shared_removed=[]
old_terminal_pads=[q for f in b.GetFootprints() if f.GetReference() in placements for q in f.Pads() if q.GetNetname() in ['GND','+5V','/RELAY_1','/RELAY_2']]
for t in original_tracks:
 if isinstance(t,p.PCB_VIA):continue
 if t.GetNetname() in ['/RELAY_1','/RELAY_2'] and t.GetLayer()==p.F_Cu and all(137<=p.ToMM(v.x)<=158 and 104<=p.ToMM(v.y)<=118 for v in [t.GetStart(),t.GetEnd()]):shared_removed.append(t.m_Uuid.AsString());b.Remove(t);continue
 if t.GetLength()>p.FromMM(5):continue
 if any(q.GetNetname()==t.GetNetname() and p.SHAPE.Collide(q.GetEffectiveShape(t.GetLayer()),t.GetEffectiveShape(t.GetLayer()),0) for q in old_terminal_pads):shared_removed.append(t.m_Uuid.AsString());b.Remove(t)
for t in original_tracks:
 if t.m_Uuid.AsString() not in shared_removed and t.GetNetname() in private:removed.append(t.m_Uuid.AsString());b.Remove(t)
oldpads={};changes=[];footprints={f.GetReference():f for f in b.GetFootprints()}
for ref,(x,y,a) in placements.items():
 f=footprints[ref];oldpads[ref]={q.GetNumber():[p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y),q.GetNetname()] for q in f.Pads() if q.GetNumber()};old=[p.ToMM(f.GetPosition().x),p.ToMM(f.GetPosition().y),f.GetOrientationDegrees()]
 f.SetOrientationDegrees(a);f.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)));changes.append(dict(ref=ref,before=old,after=[x,y,a]))
# Keep revision1.1d copper-branding assets intact: add development identification on documentation layer.
t=p.PCB_TEXT(b);t.SetText('REV 1.2 DEVELOPMENT - RELAY BAY CANDIDATE - NOT FOR MANUFACTURE');t.SetLayer(p.Dwgs_User);t.SetPosition(p.VECTOR2I(p.FromMM(128),p.FromMM(160)));t.SetTextSize(p.VECTOR2I(p.FromMM(1),p.FromMM(1)));b.Add(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(P/'abx-motion.kicad_pcb'),b)
(O/'changes.json').write_text(json.dumps(dict(moved=changes,private_nets=sorted(private),removed_private_tracks=removed,removed_shared_terminal_stubs=shared_removed,oldpads=oldpads),indent=2)+'\n');print('Placed',len(changes),'components; removed',len(removed),'relay-private track/via objects only.')
