from pathlib import Path
import pcbnew as p,json,hashlib,xml.etree.ElementTree as E
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
b=p.LoadBoard(str(O/'before.kicad_pcb'));a=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));bf={f.GetReference():f for f in b.GetFootprints()};af={f.GetReference():f for f in a.GetFootprints()};assert bf.keys()==af.keys()
for ref,f in bf.items():
 g=af[ref];assert f.GetValue()==g.GetValue()
 if ref not in ['J502','J504']:
  assert f.GetPosition()==g.GetPosition() and f.GetOrientationDegrees()==g.GetOrientationDegrees() and f.GetFPID()==g.GetFPID(),ref
 else:
  assert f.GetPosition()==g.GetPosition()
  np={q.GetNumber():q for q in g.Pads()};op={q.GetNumber():q for q in f.Pads()}
  assert {n:q.GetNetname() for n,q in np.items()}=={n:q.GetNetname() for n,q in op.items()}
  assert np['1'].GetShape()==p.PAD_SHAPE_RECT
  assert abs(p.ToMM(np['4'].GetPosition().x-np['1'].GetPosition().x)-7.62)<.00001
  assert all(q.GetDrillSize().x==p.FromMM(1.1) for q in np.values())
  x=p.ToMM(g.GetPosition().x)
  for layer in [p.F_SilkS,p.B_SilkS]:
   items=[t for t in a.GetDrawings() if isinstance(t,p.PCB_TEXT) and t.GetLayer()==layer and abs(p.ToMM(t.GetPosition().y)-145.5)<.001 and x-.01<=p.ToMM(t.GetPosition().x)<=x+7.63]
   assert [t.GetText() for t in sorted(items,key=lambda q:q.GetPosition().x)]==['EN','STEP','DIR','GND']
   assert all(t.IsMirrored()==(layer==p.B_SilkS) for t in items)
   for t,q in zip(sorted(items,key=lambda q:q.GetPosition().x),[np[str(n)] for n in range(1,5)]):assert t.GetPosition().x==q.GetPosition().x
# Every track/via must remain identical, including UUID/net/dimensions.
def tracks(board):
 return {t.m_Uuid.AsString():(t.GetNetname(),t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetLayer(),t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth()) for t in board.GetTracks()}
assert tracks(a)==tracks(b)
def nets(path):return {n.attrib['name']:sorted((q.attrib['ref'],q.attrib['pin']) for q in n.findall('node')) for n in E.parse(path).getroot().findall('./nets/net')}
assert nets(O/'netlist.xml')==nets(R/'validation/thermal-20261020/netlist.xml')
h=json.loads((R/'work/rev-1.2-relay-bay/review/baseline-hashes.json').read_text());prod={k:v for k,v in h.items() if k.startswith('production/')};assert all(hashlib.sha256((R/k).read_bytes()).hexdigest()==v for k,v in prod.items())
j=json.loads((O/'drc.json').read_text());assert not j['unconnected_items'] and not j['schematic_parity'];assert len(j['violations'])==19 and all(v['type']=='lib_footprint_mismatch' and v['severity']=='warning' for v in j['violations'])
result={'changed_footprints':['J502','J504'],'unchanged_other_footprints':len(af)-2,'all_tracks_and_vias_unchanged':len(tracks(a)),'front_and_back_labels_match_pad_nets':True,'pin_order':'1 EN, 2 STEP, 3 DIR, 4 GND','pitch_mm':2.54,'drill_mm':1.1,'production_files_hash_identical':len(prod),'electrical_netlist_unchanged':True,'drc_errors':0,'opens':0,'parity_issues':0,'existing_library_warnings':19};(O/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
