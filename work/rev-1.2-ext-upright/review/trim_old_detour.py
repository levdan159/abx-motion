from pathlib import Path
import pcbnew as p,json
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));ids=set(json.loads((O/'local-detour.json').read_text())['new_tracks']);tracks=list(b.GetTracks());removed=[]
for t in tracks:
 if t.m_Uuid.AsString() in ids:removed.append(t.m_Uuid.AsString());b.Remove(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'trimmed-detour.json').write_text(json.dumps(removed,indent=2))
