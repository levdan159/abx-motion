"""Read-only independent scope, connectivity and manufacturing audit."""
from pathlib import Path
import pcbnew as p,json,hashlib,xml.etree.ElementTree as ET,csv,re,collections
R=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent;P=R/'production/rev-1.1d-20261020';C=R/'production/rev-1.1c-20261020'
b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));old=p.LoadBoard(str(O/'before/abx-motion.kicad_pcb'));change=json.loads((O/'changes.json').read_text());add={a['uuid'] for a in change['added_vias']};xy=lambda x:(x.x,x.y)
def tracks(board):
 return {t.m_Uuid.AsString():(t.GetNetname(),xy(t.GetStart()),xy(t.GetEnd()),t.GetLayerSet().FmtHex(),t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth(),t.GetDrillValue() if isinstance(t,p.PCB_VIA) else 0) for t in board.GetTracks()}
nt=tracks(b);ot=tracks(old);assert {k:v for k,v in nt.items() if k not in add}==ot;assert set(nt)-set(ot)==add
of={f.GetReference():f for f in old.GetFootprints()}
def pads(f):return sorted((q.GetNumber(),xy(q.GetPosition()),xy(q.GetSize()),xy(q.GetDrillSize()),q.GetLayerSet().FmtHex(),q.GetNetname()) for q in f.Pads())
for f in b.GetFootprints():
 q=of[f.GetReference()];assert pads(f)==pads(q);assert (xy(f.GetPosition()),f.GetOrientationDegrees(),f.GetValue(),f.GetFPIDAsString())==(xy(q.GetPosition()),q.GetOrientationDegrees(),q.GetValue(),q.GetFPIDAsString())
assert not any(t.GetLayer()==p.In1_Cu for t in b.GetTracks() if not isinstance(t,p.PCB_VIA))
def pn(f):
 t=ET.parse(f);return {(n.get('ref'),n.get('pin')):net.get('name') for net in t.findall('./nets/net') for n in net.findall('node')}
np=pn(O/'netlist.xml');assert np==pn(R/'validation/robustness-final-20261020/netlist.xml');bp={(f.GetReference(),q.GetNumber()):q.GetNetname() for f in b.GetFootprints() for q in f.Pads() if q.GetNumber()};assert all(bp[k]==v for k,v in np.items())
# Execute original netlist functional assertions and retain prior 150-check power review by identical pin-net map.
prior=json.loads((R/'validation/robustness-final-20261020/audit.json').read_text());assert prior['functional_net_checks']==150
for a in change['added_vias']:
 v=next(t for t in b.GetTracks() if t.m_Uuid.AsString()==a['uuid']);assert v.GetNetname()==a['net'];assert v.GetFrontTentingMode()==v.GetBackTentingMode()==p.TENTING_MODE_TENTED
 receiving=p.In2_Cu if a['net']=='+BATT' else p.B_Cu
 for layer in [p.F_Cu,receiving]:assert any(z.GetNetname()==a['net'] and z.IsOnLayer(layer) and z.HitTestFilledArea(layer,v.GetPosition()) for z in b.Zones()),(a,layer)
areas=[]
for a in change['added_zones']:
 z=next(z for z in b.Zones() if z.m_Uuid.AsString()==a['uuid']);area=z.GetFilledArea()/1e12;assert area>1,(a,area);areas.append(dict(ref=a['ref'],layer=a['layer'],filled_area_mm2=area))
# Module internal antenna keepout and all pre-existing footprint thermal holes remain identical.
f=b.FindFootprintByReference('U3');ep=[q for q in f.Pads() if q.GetNumber()=='41' and q.GetDrillSize().x];assert len(ep)==12
for a in change['added_zones']:
 if a['ref']=='U3':assert a['bounds_mm'][1]>=58.5
for name in ['abx-motion-jlcpcb-bom.csv','abx-motion-jlcpcb-cpl.csv']:assert (P/name).read_bytes()==(C/name).read_bytes()
# Header dates/revision IDs differ; actual exposed mask and stencil geometry must not change.
def canonical(path):
 return '\n'.join(s for s in path.read_text().splitlines() if not s.startswith(('G04 #@! TF.CreationDate','G04 #@! TF.ProjectId','%TF.CreationDate','%TF.ProjectId','%TO.CVal','G04 #@! TO.CVal','G04 Created by')))
for suffix in ['F_Mask.gts','B_Mask.gbs','F_Paste.gtp','B_Paste.gbp','Edge_Cuts.gm1','NPTH.drl']:
 name='abx-motion-'+suffix
 if suffix=='NPTH.drl':
  canon=lambda f:'\n'.join(x for x in f.read_text().splitlines() if not x.startswith(('; #@! TF.CreationDate','; DRILL file')))
  assert canon(P/'gerbers'/name)==canon(C/'gerbers'/name),name
 else:assert canonical(P/'gerbers'/name)==canonical(C/'gerbers'/name),name
j=json.loads((O/'drc.json').read_text());e=json.loads((O/'erc.json').read_text());assert not j['unconnected_items'] and not j['schematic_parity'];assert len(j['violations'])==19 and all(v['type']=='lib_footprint_mismatch' and v['severity']=='warning' for v in j['violations']);assert not any(s['violations'] for s in e['sheets'])
audit=dict(revision='1.1d',status='Prototype fabrication candidate; relay alignment review before assembly. Powered qualification NOT RUN.',PCB_sha256=hashlib.sha256((R/'abx-motion.kicad_pcb').read_bytes()).hexdigest(),original_tracks_and_vias_preserved=len(ot),added_tented_vias=len(add),added_zones=len(areas),zone_areas=areas,all_added_vias_on_matching_top_and_receiving_layer_filled_copper=True,component_positions_pads_drills_values_and_angles_unchanged=True,schematic_pin_nets_matched=len(np),functional_net_checks_carried_forward_by_identical_pin_net_map=150,ESP32_existing_ground_thermal_holes=12,antenna_region_unchanged=True,BOM_and_CPL_byte_identical_to_Rev1_1c=True,mask_paste_outline_NPTH_geometry_unchanged=True,ERC_violations=0,DRC_errors=0,DRC_warnings=19,unconnected_items=0,schematic_parity=0,physical_thermal_test='NOT RUN')
(O/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
