from pathlib import Path
import pcbnew as p,json,hashlib,xml.etree.ElementTree as E,collections,csv,math
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
before=p.LoadBoard(str(O/'before.kicad_pcb'));after=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));bf={f.GetReference():f for f in before.GetFootprints()};af={f.GetReference():f for f in after.GetFootprints()};c=json.loads((O/'changes.json').read_text());allowed={x['ref'] for x in c['moved']};assert len(allowed)==16;assert bf.keys()==af.keys()
for ref,f in bf.items():
 g=af[ref];assert f.GetValue()==g.GetValue() and f.GetFPID()==g.GetFPID(),ref
 if ref not in allowed:assert f.GetPosition()==g.GetPosition() and f.GetOrientationDegrees()==g.GetOrientationDegrees(),ref
 def pads(fp):return sorted((q.GetNumber(),q.GetNetname(),q.GetDrillSize().x,q.GetDrillSize().y,q.GetSize().x,q.GetSize().y) for q in fp.Pads())
 assert pads(f)==pads(g),ref
bt={t.m_Uuid.AsString():t for t in before.GetTracks()};at={t.m_Uuid.AsString():t for t in after.GetTracks()}
def width(t):return t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth()
def sig(t):return (t.GetNetname(),t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetLayer(),width(t))
for uid in bt.keys()&at.keys():assert sig(bt[uid])==sig(at[uid]),uid
removed=bt.keys()-at.keys();expected=set(c['removed_tracks'])|set(json.loads((O/'polish.json').read_text())['removed_unused_vias']);assert removed<=expected,removed-expected
allowednets=set(c['private_nets'])|{'GND','+5V','/RELAY_1','/RELAY_2'}
for uid in at.keys()-bt.keys():assert at[uid].GetNetname() in allowednets,at[uid].GetNetname()
thermal=json.loads((R/'validation/thermal-20261020/changes.json').read_text())
for v in thermal['added_vias']:assert v['uuid'] in at and sig(bt[v['uuid']])==sig(at[v['uuid']])
def zones(b):return {z.m_Uuid.AsString():(z.GetNetname(),z.GetLayer(),z.Outline().Format()) for z in b.Zones()}
assert zones(before)==zones(after),'Zone outlines/nets changed'
contacts={q.GetNetname() for ref in ['J505','J506'] for q in af[ref].Pads()}
for t in after.GetTracks():
 if t.GetNetname() in contacts:assert not isinstance(t,p.PCB_VIA) and width(t)>=p.FromMM(.8)
# Labels tell the electrical truth: LEDs are coil-drive indicators, not contact feedback.
for n in [1,2]:
 q={x.GetNumber():x.GetNetname() for x in af[f'D50{2*n}'].Pads()};assert q['1'].endswith(f'RLY{n}_COIL_N') and q['2'].endswith(f'RLY{n}_LED_A')
 j={x.GetNumber():x.GetNetname().split('/')[-1] for x in af[f'J50{4+n}'].Pads()};assert j=={'1':f'RLY{n}_NO','2':f'RLY{n}_COM','3':f'RLY{n}_NC'}
# Manufacturing files remain byte-identical.
h=json.loads((R/'work/rev-1.2-relay-bay/review/baseline-hashes.json').read_text());prod={k:v for k,v in h.items() if k.startswith('production/')}
assert all(hashlib.sha256((R/k).read_bytes()).hexdigest()==v for k,v in prod.items())
def nets(path):return {n.attrib['name']:sorted((q.attrib['ref'],q.attrib['pin']) for q in n.findall('node')) for n in E.parse(path).getroot().findall('./nets/net')}
assert nets(O/'netlist.xml')==nets(R/'validation/thermal-20261020/netlist.xml')
drc=json.loads((O/'drc.json').read_text());assert not drc['unconnected_items'];assert not drc['schematic_parity'];assert all(v['type']=='lib_footprint_mismatch' and v['severity']=='warning' for v in drc['violations'])
with (O/'native-placement-changes.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['Reference','Old X','Old Y','Old angle','New X','New Y','New native angle'])
 for item in c['moved']:w.writerow([item['ref']]+item['before']+item['after'])
result={'moved_footprints':len(allowed),'unchanged_footprints':len(bf)-len(allowed),'unchanged_retained_tracks_vias':len(bt.keys()&at.keys()),'removed_local_tracks_vias':len(removed),'new_local_tracks_vias':len(at.keys()-bt.keys()),'preserved_thermal_vias':len(thermal['added_vias']),'zone_outlines_and_nets_unchanged':True,'production_files_hash_identical':len(prod),'electrical_netlist_unchanged':True,'contact_tracks':sum(t.GetNetname() in contacts for t in after.GetTracks()),'drc_errors':0,'opens':0,'parity_issues':0,'existing_library_warnings':len(drc['violations'])}
(O/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
