"""Read-only electrical review and analytical corner cases; NOT a powered test."""
from pathlib import Path
from itertools import product
import xml.etree.ElementTree as ET,xml.etree.ElementTree as X,csv,json,math,hashlib,ast,collections
import pcbnew as p
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];PROD=ROOT/'production/rev-1.1c-20261020'
b=p.LoadBoard(str(ROOT/'abx-motion.kicad_pcb'));before=p.LoadBoard(str(OUT/'before/abx-motion.kicad_pcb'))
fs={f.GetReference():f for f in b.GetFootprints()};oldfs={f.GetReference():f for f in before.GetFootprints()}
xy=lambda v:(v.x,v.y)
def tracks(board):
 return {t.m_Uuid.AsString():(t.GetNetname(),xy(t.GetStart()),xy(t.GetEnd()),t.GetLayerSet().FmtHex(),t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth(),t.GetDrillValue() if isinstance(t,p.PCB_VIA) else 0) for t in board.GetTracks()}
assert tracks(b)==tracks(before)
for ref,f in fs.items():
 o=oldfs[ref]
 def pads(x):return sorted((q.GetNumber(),xy(q.GetPosition()),xy(q.GetSize()),xy(q.GetDrillSize()),q.GetNetname(),q.GetLayerSet().FmtHex()) for q in x.Pads())
 assert pads(f)==pads(o),ref
 assert (xy(f.GetPosition()),f.GetOrientationDegrees(),f.GetFPIDAsString())==(xy(o.GetPosition()),o.GetOrientationDegrees(),o.GetFPIDAsString()),ref
 if ref in ['R302','R402']:assert f.GetValue()=='12k' and f.GetField('LCSC').GetText()=='C22790'
 else:assert f.GetValue()==o.GetValue(),ref
assert not any(t.GetLayer()==p.In1_Cu for t in b.GetTracks() if not isinstance(t,p.PCB_VIA))
manifest=json.load(open(ROOT/'production/rev-1.1b-20261020/manifest.json'))
assert hashlib.sha256((ROOT/'abx-motion.kicad_pro').read_bytes()).hexdigest()==manifest['abx-motion.kicad_pro']
root=ET.parse(OUT/'netlist.xml');pn={(n.get('ref'),n.get('pin')):net.get('name') for net in root.findall('./nets/net') for n in net.findall('node')}
old=ET.parse(ROOT/'validation/rev-1.1b-20261020/netlist.xml');opn={(n.get('ref'),n.get('pin')):net.get('name') for net in old.findall('./nets/net') for n in net.findall('node')};assert pn==opn
bp={(f.GetReference(),q.GetNumber()):q.GetNetname() for f in b.GetFootprints() for q in f.Pads() if q.GetNumber()};assert all(bp[k]==v for k,v in pn.items())
prior=(ROOT/'validation/final-run-20261020/complete_review.py').read_text();block=prior.split('# Netlist-driven functional review, independent of the router\'s completion count.')[1].split('# Every schematic pin')[0];ctx={'ET':ET,'OUT':OUT};exec(block.replace('netlist-after.xml','netlist.xml'),ctx);checks=ctx['checks']
def same(label,*nodes):
 ns=[pn[n] for n in nodes];assert len(set(ns))==1,(label,ns);checks.append(label)
def net(label,node,n):assert pn[node]==n,(label,pn[node],n);checks.append(label)
# Independent power-stage/fault/charge-pump pin checks against the manufacturer pin table.
for ch,base in [(1,300),(2,400)]:
 u='U'+str(base+1);rc='R'+str(base+2);rh='R'+str(base+1);sh='R'+str(base+9)
 net(f'M{ch} VM',(u,'1'),'+BATT');net(f'M{ch} SN',(u,'20'),'GND');net(f'M{ch} VREF bottom',(rc,'2'),'GND')
 same(f'M{ch} VREF divider',(u,'6'),(rh,'2'),(rc,'1'));same(f'M{ch} VREF top AVDD',(u,'7'),(rh,'1'))
 same(f'M{ch} current SP',(u,'21'),(sh,'1'));net(f'M{ch} shunt return',(sh,'2'),'GND')
 same(f'M{ch} charge-pump VM',('C'+str(base+1),'1'),(u,'1'));same(f'M{ch} charge-pump VCP',('C'+str(base+1),'2'),(u,'2'))
 same(f'M{ch} flying-cap CPH',('C'+str(base+2),'1'),(u,'3'));same(f'M{ch} flying-cap CPL',('C'+str(base+2),'2'),(u,'4'))
 same(f'M{ch} sleep E-stop',(f'R{base+3}','1'),('J102','2'));same(f'M{ch} sleep path',(f'R{base+3}','2'),(u,'13'))
 net(f'M{ch} gate-current setting',(f'R{base+12}','2'),'GND');same(f'M{ch} gate-current pin',(u,'12'),(f'R{base+12}','1'))
 net(f'M{ch} fault GPIO',(u,'9'),f'/M{ch}_nFAULT');net(f'M{ch} PH GPIO',(u,'15'),f'/M{ch}_PWM_PH');net(f'M{ch} EN GPIO',(u,'14'),f'/M{ch}_PWM_EN')
 for qn,kind,side in [(base+1,'H',1),(base+2,'L',1),(base+3,'H',2),(base+4,'L',2)]:
  q='Q'+str(qn)
  for pin in ['1','2','3']:net(f'{q} source {pin}',(q,pin),f'/DC_Motor_{ch}/MOT_OUT{side}' if kind=='H' else f'/DC_Motor_{ch}/SHUNT_SP')
  net(f'{q} drain',(q,'5'),'+BATT' if kind=='H' else f'/DC_Motor_{ch}/MOT_OUT{side}')
net('Reverse-FET source',('Q1','1'),'+BATT');same('Reverse-FET drain/fuse',('Q1','5'),('F1','2'));same('Gate zener reference',('D1','1'),('Q1','1'));same('Gate zener clamp',('D1','2'),('Q1','4'),('R1','1'));net('Gate bias return',('R1','2'),'GND')
# Resistor tolerance, AVDD 4.4–5.2V, gain18–22; model offset0–250mV.
# VOFF has typ50mV/max250mV but no guaranteed min: zero is a modelling floor, not a guaranteed threshold bound.
def sweep(bottom):
 cases=[]
 for avdd,hi,lo,gain,off,rs in product([4.4,5.2],[18000*.99,18000*1.01],[bottom*.99,bottom*1.01],[18,22],[0,.25],[.0099,.0101]):
  vr=avdd*lo/(hi+lo);i=(vr-off)/(gain*rs);cases.append(dict(AVDD_V=avdd,Rhigh_ohm=hi,Rlow_ohm=lo,gain=gain,offset_V=off,shunt_ohm=rs,VREF_V=vr,I_chop_A=i,shunt_W=i*i*rs))
 return {'cases':len(cases),'nominal_I_A':(4.8*bottom/(18000+bottom)-.05)/(.01*20),'min':min(cases,key=lambda x:x['I_chop_A']),'max':max(cases,key=lambda x:x['I_chop_A']),'max_shunt_W':max(x['shunt_W'] for x in cases)}
corners={'old_30k':sweep(30000),'new_12k':sweep(12000),'scope':'Analytical static estimates; exclude resistor TCR, PCB ground/Kelvin errors, comparator delay/blanking and thermal feedback. Not guaranteed motor peak-current bounds.'}
assert corners['new_12k']['max_shunt_W']<1.5 and corners['old_30k']['max_shunt_W']>3
# Current-ramp sensitivity during the specified 2us blanking interval: conservative no-resistance/no-back-EMF illustration.
blanking=[{'L_uH':l,'extra_current_during_2us_blank_A_at32V':32*2e-6/(l*1e-6)} for l in [1,5,10,50,100,1000]]
losses={'24V_two_150W_bus_A':12.5,'Q1_cold_loss_W_at_12_5A':12.5**2*.018,'Q1_loss_W_assuming_2x_cold_Rds_for_sensitivity':12.5**2*.036,'Hbridge_two_FET_conduction_W_at_6_25A_using_3_3mOhm':2*6.25**2*.0033,'shunt_W_at_6_25A':6.25**2*.01,'gate_Qmax_10V_nC':53,'gate_nominal_25mA_charge_time_us':53e-9/.025*1e6,'gate_drive_time_us':2.5,'scope':'Loss estimates, not junction-temperature qualification; use phase current rather than battery current under PWM. Switching losses are not included in conduction estimates.'}
# New resistor polarity/angle check from current supplier SVG; both lead centers must land on the correct native copper.
svg=X.parse(OUT/'datasheets/C22790-1.svg').getroot();g=next(x for x in svg if 'c_para' in x.attrib);ox,oy=map(float,g.attrib['c_origin'].split(','));sp={}
for q in g.iter():
 if q.attrib.get('c_partid')=='part_pad':x,y=map(float,q.attrib['c_origin'].split(','));sp[q.attrib['number']]=((x-ox)*.254,(y-oy)*.254)
cpl=list(csv.DictReader(open(PROD/'abx-motion-jlcpcb-cpl.csv')));ocpl={r['Designator']:r for r in csv.DictReader(open(OUT/'before/production/abx-motion-jlcpcb-cpl.csv'))}
for row in cpl:
 old=ocpl[row['Designator']].copy()
 if row['Designator'] in ['R302','R402']:old['Val']='12k'
 assert row==old
 if row['Designator'] not in ['R302','R402']:continue
 f=fs[row['Designator']];a=math.radians(-float(row['Rotation']));co,si=math.cos(a),math.sin(a);cx=float(row['Mid X'].replace('mm',''));cy=-float(row['Mid Y'].replace('mm',''))
 for n,(x,y) in sp.items():
  pt=p.VECTOR2I(p.FromMM(cx+co*x-si*y),p.FromMM(cy+si*x+co*y));q=next(q for q in f.Pads() if q.GetNumber()==n);assert p.SHAPE.Collide(q.GetEffectiveShape(p.F_Cu),p.SHAPE_CIRCLE(pt,p.FromMM(.003)),0)
bom=list(csv.DictReader(open(PROD/'abx-motion-jlcpcb-bom.csv')));refs={r for row in bom for r in row['Designator'].split(',')};assert refs==set(ocpl) and len(refs)==len(cpl)==239 and len(bom)==66
for ref in ['R302','R402']:
 co=next(x for x in root.findall('./components/comp') if x.attrib['ref']==ref);assert co.find('value').text=='12k'
d=json.load(open(OUT/'drc.json'));e=json.load(open(OUT/'erc.json'));assert not any(v['severity']=='error' for v in d['violations']);assert not d['unconnected_items'] and not d['schematic_parity'];assert not any(x['violations'] for x in e['sheets'])
assert len(d['violations'])==19 and all(v['type']=='lib_footprint_mismatch' for v in d['violations'])
result={'revision':'1.1c','status':'Design checks pass: prototype fabrication candidate. Confirm relay alignment before assembly. Physical motor/thermal/fault qualification follows prototype receipt; return-energy operating envelope remains unqualified.','PCB_sha256':hashlib.sha256((ROOT/'abx-motion.kicad_pcb').read_bytes()).hexdigest(),'schematic_pin_nets_matched':len(pn),'functional_net_checks':len(checks),'functional_checks':checks,'tracks_and_vias_unchanged':len(tracks(b)),'pads_positions_holes_nets_unchanged':True,'In1_signal_tracks':0,'BOM_groups':66,'placements':239,'new_resistor_supplier_pad_check':'PASS','all_placement_angles_positions_unchanged':True,'ERC_violations':0,'DRC_errors':0,'unconnected_items':0,'schematic_parity':0,'DRC_warnings':19,'physical_motor_tests':'NOT RUN','physical_thermal_tests':'NOT RUN','physical_short_tests':'NOT RUN','physical_regeneration_tests':'NOT RUN','firmware_safety_logic':'NOT IMPLEMENTED / NOT TESTED by this hardware pass'}
for name,obj in [('audit.json',result),('current-corners.json',corners),('blanking-sensitivity.json',blanking),('loss-estimates.json',losses)]: (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='functional_checks'},indent=2));print('Current model:',{k:(v['nominal_I_A'],v['min']['I_chop_A'],v['max']['I_chop_A'],v['max_shunt_W']) for k,v in corners.items() if isinstance(v,dict)})
