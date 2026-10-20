from pathlib import Path
import pcbnew as p,json
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));j=json.loads((O/'placement-drc.json').read_text());bad={i['uuid'] for v in j['violations'] if v['severity']=='error' for i in v['items']};tracks=list(b.GetTracks());removed=[]
for t in tracks:
 if t.m_Uuid.AsString() in bad:
  assert t.GetNetname() in ['/MCU_and_Encoders/BTN_BACK','/+3V3_DRV_EN','+3V3']
  removed.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname()});b.Remove(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'collision-ripup.json').write_text(json.dumps(removed,indent=2));print('Ripped',len(removed),'local collisions for automatic rerouting.')
