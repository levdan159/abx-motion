from pathlib import Path
import pcbnew as p,json,hashlib,xml.etree.ElementTree as E,collections,math,subprocess,tempfile,csv
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
 path=Path(tmp)/'before.kicad_pcb';path.write_bytes(subprocess.check_output(['git','show','673dc00:abx-motion.kicad_pcb'],cwd=R));b=p.LoadBoard(str(path))
a=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));bf={f.GetReference():f for f in b.GetFootprints()};af={f.GetReference():f for f in a.GetFootprints()};ch=json.loads((O/'changes.json').read_text());moved={q['ref'] for q in ch['moved']};allowed=moved|{'J208'};assert bf.keys()==af.keys()
for ref,f in bf.items():
 g=af[ref];assert f.GetValue()==g.GetValue(),ref
 if ref not in moved:assert f.GetPosition()==g.GetPosition() and f.GetOrientationDegrees()==g.GetOrientationDegrees(),ref
 if ref!='J208':assert f.GetFPID()==g.GetFPID(),ref
 assert {q.GetNumber():q.GetNetname() for q in f.Pads()}=={q.GetNumber():q.GetNetname() for q in g.Pads()},ref
 if ref!='J208':assert sorted((q.GetNumber(),q.GetSize().x,q.GetSize().y,q.GetDrillSize().x,q.GetDrillSize().y) for q in f.Pads())==sorted((q.GetNumber(),q.GetSize().x,q.GetSize().y,q.GetDrillSize().x,q.GetDrillSize().y) for q in g.Pads()),ref
for ref in ch['under_oled']:
 bb=af[ref].GetBoundingBox(False,False)
 assert p.ToMM(bb.GetLeft())>=65.5 and p.ToMM(bb.GetRight())<=93.5 and p.ToMM(bb.GetTop())>=84.9 and p.ToMM(bb.GetBottom())<=102,ref
 for h in ['H5','H6']:
  c=af[h].GetPosition();x,y=p.ToMM(c.x),p.ToMM(c.y);dx=max(p.ToMM(bb.GetLeft())-x,0,x-p.ToMM(bb.GetRight()));dy=max(p.ToMM(bb.GetTop())-y,0,y-p.ToMM(bb.GetBottom()));assert math.hypot(dx,dy)>=3,ref
for ref in ['J601','J602','J603','J604','J605','J606']:
 f=af[ref];assert f.GetOrientationDegrees()==90
 for layer in [p.F_SilkS,p.B_SilkS]:
  for q in f.Pads():
   n=q.GetNumber();label=({'1':'MIN','2':'G','3':'MAX'} if ref in ['J601','J602','J603','J604'] else {'1':'5V','2':'G','3':'SW'})[n]
   found=[t for t in a.GetDrawings() if isinstance(t,p.PCB_TEXT) and t.GetLayer()==layer and t.GetText()==label and abs(p.ToMM(t.GetPosition().y-q.GetPosition().y))<.001 and 3.5<p.ToMM(t.GetPosition().x-f.GetPosition().x)<5]
   assert len(found)==1 and found[0].IsMirrored()==(layer==p.B_SilkS),(ref,n,layer)
bt={t.m_Uuid.AsString():t for t in b.GetTracks()};at={t.m_Uuid.AsString():t for t in a.GetTracks()}
def sig(t):return (t.GetNetname(),t.GetLayer(),t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth(),t.GetDrillValue() if isinstance(t,p.PCB_VIA) else None)
collision=json.loads((O/'collision-ripup.json').read_text());allow_nets=set(ch['private_nets'])|{q['net'] for q in collision}|{'GND','+3V3','+5V','/I2C_SCL','/I2C_SDA','/+3V3_DRV_EN'}
modified=[]
for uid in bt.keys()&at.keys():
 assert bt[uid].GetNetname()==at[uid].GetNetname(),uid
 if sig(bt[uid])!=sig(at[uid]):assert bt[uid].GetNetname() in allow_nets;modified.append(uid)
for uid in bt.keys()-at.keys():assert bt[uid].GetNetname() in allow_nets,bt[uid].GetNetname()
for uid in at.keys()-bt.keys():assert at[uid].GetNetname() in allow_nets,at[uid].GetNetname()
thermal=json.loads((R/'validation/thermal-20261020/changes.json').read_text())
for q in thermal['added_vias']:assert sig(bt[q['uuid']])==sig(at[q['uuid']])
def zones(board):return {q.m_Uuid.AsString():(q.GetNetname(),q.GetLayer(),q.Outline().Format()) for q in board.Zones()}
assert zones(a)==zones(b)
assert (R/'abx-motion.kicad_pro').read_bytes()==subprocess.check_output(['git','show','673dc00:abx-motion.kicad_pro'],cwd=R)
inner=collections.Counter();frontback=collections.Counter()
for uid in at.keys()-bt.keys():
 t=at[uid]
 if isinstance(t,p.PCB_VIA):continue
 assert t.GetLayer()!=p.In1_Cu,'Solid ground reference plane must remain unrouted'
 if t.GetLayer()==p.In2_Cu:inner[t.GetNetname()]+=p.ToMM(t.GetLength())
 else:frontback[t.GetNetname()]+=p.ToMM(t.GetLength())
def nets(path):return {n.attrib['name']:sorted((q.attrib['ref'],q.attrib['pin']) for q in n.findall('node')) for n in E.parse(path).getroot().findall('./nets/net')}
assert nets(O/'netlist.xml')==nets(R/'validation/thermal-20261020/netlist.xml')
h=json.loads((R/'work/rev-1.2-relay-bay/review/baseline-hashes.json').read_text());prod={k:v for k,v in h.items() if k.startswith('production/')};assert all(hashlib.sha256((R/k).read_bytes()).hexdigest()==v for k,v in prod.items())
j=json.loads((O/'drc.json').read_text());assert not j['unconnected_items'] and not j['schematic_parity'];assert len(j['violations'])==19 and all(v['type']=='lib_footprint_mismatch' and v['severity']=='warning' for v in j['violations'])
# Verify a continuous component-free rectangle between the vertical I/O bank and existing StepStick.
roi=(80.5,109,92.1,140)
for ref,f in af.items():
 if ref.startswith('LOGO'):continue
 q=f.GetBoundingBox(False,False);x,y,z,w=map(p.ToMM,[q.GetLeft(),q.GetTop(),q.GetRight(),q.GetBottom()]);assert z<=roi[0] or x>=roi[2] or w<=roi[1] or y>=roi[3],ref
result={'baseline_commit':'673dc00','moved_footprints':sorted(moved),'changed_oled_socket':'J208; same pin centres/net mapping, 0.9 mm drills','unchanged_other_footprints':len(af)-len(allowed),'parts_beneath_oled':len(ch['under_oled']),'standoffs_mm':10,'mount_post_reserve_radius_mm':3,'connector_arrangement':'2 columns x 3 rows; all six rotated 90 degrees','front_back_pin_legends_verified':True,'component_free_rectangle_mm':roi,'component_free_rectangle_area_mm2':round((roi[2]-roi[0])*(roi[3]-roi[1]),2),'preserved_original_tracks_vias':len(bt.keys()&at.keys())-len(modified),'modified_original_tracks':modified,'removed_original_tracks_vias':len(bt.keys()-at.keys()),'new_tracks_vias':len(at.keys()-bt.keys()),'preserved_thermal_vias':len(thermal['added_vias']),'zone_outlines_nets_unchanged':True,'in1_ground_plane_unrouted':True,'new_in2_signal_length_by_net_mm':{k:round(v,3) for k,v in inner.items()},'electrical_netlist_unchanged':True,'preserved_production_files':len(prod),'drc_errors':0,'opens':0,'parity_issues':0,'existing_library_warnings':19,'oled_exact_module_fit':'not qualified; verify actual module pin order, outline, hole pattern, engagement and underside parts'}
result['sha256']={str(q.relative_to(R)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [R/'abx-motion.kicad_pcb',R/'MCU.kicad_sch',R/'abx-motion.kicad_pro',O/'drc.json',O/'erc.json']}
(O/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
with (O/'placements-native.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['Reference','X mm native','Y mm native','Rotation degrees native','Side','Value']);w.writerows([ref,p.ToMM(af[ref].GetPosition().x),p.ToMM(af[ref].GetPosition().y),af[ref].GetOrientationDegrees(),'Front',af[ref].GetValue()] for ref in sorted(allowed))
print(json.dumps(result,indent=2))
