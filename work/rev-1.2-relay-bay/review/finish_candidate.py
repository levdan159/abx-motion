from pathlib import Path
import pcbnew as p,json
O=Path(__file__).resolve().parent;P=O.parent;b=p.LoadBoard(str(P/'abx-motion.kicad_pcb'));j=json.loads((O/'routed-drc.json').read_text());unused={i['uuid'] for v in j['violations'] if v['type']=='via_dangling' for i in v['items']};assert len(unused)==4
items=list(b.GetTracks());removed=[]
for t in items:
 if t.m_Uuid.AsString() in unused:
  assert isinstance(t,p.PCB_VIA) and t.GetNetname() in ['+5V','/RELAY_2'];assert 137<p.ToMM(t.GetPosition().x)<158 and 104<p.ToMM(t.GetPosition().y)<118;removed.append(t.m_Uuid.AsString());b.Remove(t)
b.GetTitleBlock().SetRevision('1.2-dev');b.GetTitleBlock().SetComment(0,'Relay-bay candidate only; not for manufacturing')
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(P/'abx-motion.kicad_pcb'),b)
for f in P.glob('*.kicad_sch'):f.write_text(f.read_text().replace('(rev "1.1d")','(rev "1.2-dev")'))
c=json.loads((O/'changes.json').read_text());c['removed_unused_local_vias']=removed;(O/'changes.json').write_text(json.dumps(c,indent=2)+'\n');print('Removed four obsolete relay-terminal vias; candidate marked1.2-dev.')
