"""Independent preservation and manufacturing-data checks; no PCB writes."""
from pathlib import Path
import csv, json, hashlib, re, xml.etree.ElementTree as ET, collections
import pcbnew as p
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import generate_schematics as gen
PROD=ROOT/'production/robustness-20261020';PREV=ROOT/'production/final-bom-fix-20261020'
b=p.LoadBoard(str(ROOT/'abx-motion.kicad_pcb'));old=p.LoadBoard(str(OUT/'before/abx-motion.kicad_pcb'))
fs={f.GetReference():f for f in b.GetFootprints()};ofs={f.GetReference():f for f in old.GetFootprints()}
xy=lambda a:(a.x,a.y)
def track(t):
    return (t.GetNetname(),xy(t.GetStart()),xy(t.GetEnd()),t.GetLayerSet().FmtHex(),
            t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth(),
            t.GetDrillValue() if isinstance(t,p.PCB_VIA) else 0)
ts={t.m_Uuid.AsString():track(t) for t in b.GetTracks()}
ots={t.m_Uuid.AsString():track(t) for t in old.GetTracks()}
assert all(ts.get(k)==v for k,v in ots.items()),'An original track/via changed'
assert set(fs)-set(ofs)=={'R313','R413'}
assert xy(fs['D2'].GetPosition())==xy(ofs['D2'].GetPosition())
def native_footprints(path):
    tree=gen.parse_sexp(path.read_text());result={}
    for n in tree[1:]:
        if not isinstance(n,list) or n[0]!=('sym','footprint'):continue
        ref=next(q[2][1] for q in n if isinstance(q,list) and q[:2]==[('sym','property'),('str','Reference')])
        result[ref]=n
    return result
nf=native_footprints(ROOT/'abx-motion.kicad_pcb');of=native_footprints(OUT/'before/abx-motion.kicad_pcb')
for ref in of:
    if ref not in ['D2','R2','R6']:assert of[ref]==nf[ref],('Full footprint serialization changed',ref)
def pads(f):return sorted((q.GetNumber(),xy(q.GetPosition()),xy(q.GetSize()),xy(q.GetDrillSize()),q.GetNetname(),q.GetLayerSet().FmtHex()) for q in f.Pads())
for ref,f in ofs.items():
    if ref=='D2':continue
    assert pads(f)==pads(fs[ref]),ref
    assert (xy(f.GetPosition()),f.GetOrientationDegrees(),f.GetFPIDAsString())==(
        xy(fs[ref].GetPosition()),fs[ref].GetOrientationDegrees(),fs[ref].GetFPIDAsString()),ref
    if ref not in ['R2','R6']:assert f.GetFieldsText()==fs[ref].GetFieldsText(),ref
assert (ROOT/'abx-motion.kicad_pro').read_bytes()==(OUT/'before/abx-motion.kicad_pro').read_bytes()
for name in ['MCU.kicad_sch','Industrial_IO.kicad_sch','Steppers_Relays.kicad_sch','abx-motion.kicad_sch']:
    assert (ROOT/name).read_bytes()==(OUT/'before'/name).read_bytes(),name
def nets(path):
    r=ET.parse(path)
    return {(n.get('ref'),n.get('pin')):net.get('name') for net in r.findall('./nets/net') for n in net.findall('node')}
pn=nets(OUT/'netlist.xml');before=nets(ROOT/'validation/manufacturing-gate-20261020/netlist.xml')
assert {k:v for k,v in pn.items() if k[0] not in ['D2','R313','R413']}=={k:v for k,v in before.items() if k[0]!='D2'}
bp={(f.GetReference(),q.GetNumber()):q.GetNetname() for f in b.GetFootprints() for q in f.Pads() if q.GetNumber()}
assert all(bp.get(k)==v for k,v in pn.items()),[(k,v,bp.get(k)) for k,v in pn.items() if bp.get(k)!=v]
for ref,net in [('R313','/M1_CS'),('R413','/M2_CS')]:
    assert pn[(ref,'1')]==net and pn[(ref,'2')]=='GND'
assert {k[1]:v for k,v in pn.items() if k[0]=='D2'}=={
    '1':'GND','2':'GND','3':'GND','4':'+BATT','5':'+BATT','6':'+BATT','7':'GND'}
# Repeat the established functional assertions for every limit, output and enable.
prior=(ROOT/'validation/final-run-20261020/complete_review.py').read_text()
functional=prior.split('# Netlist-driven functional review, independent of the router\'s completion count.')[1].split('# Every schematic pin')[0]
context={'ET':ET,'OUT':OUT}
exec(functional.replace('netlist-after.xml','netlist.xml'),context)
checks=context['checks']
d=json.loads((OUT/'drc.json').read_text());e=json.loads((OUT/'erc.json').read_text())
assert not [v for v in d['violations'] if v['severity']=='error']
assert not d['unconnected_items'] and not d['schematic_parity']
assert not [v for s in e['sheets'] for v in s['violations']]
assert len(d['violations'])==19 and all(v['type']=='lib_footprint_mismatch' for v in d['violations'])
assert not [t for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetLayer()==p.In1_Cu]

# Retain catalogue comments, supplier orientation corrections and strip splits.
prevbom=list(csv.DictReader((PREV/'abx-motion-jlcpcb-bom.csv').open()))
comments={r['LCSC Part #']:r['Comment'] for r in prevbom}
comments.update({'C2863624':'TVS3300DRVR','C22807':'150k','C31850':'22k'})
groups={};expected=set()
for ref,f in fs.items():
    if ref.startswith(('H','LOGO','TP_')):continue
    sku=f.GetField('LCSC').GetText();assert re.fullmatch(r'C\d+',sku),(ref,sku)
    refs=[ref+'_L',ref+'_R'] if ref in ['U501','U502'] else [ref]
    footprint='PinSocket_1x08_P2.54mm_Vertical' if len(refs)==2 else str(f.GetFPID().GetLibItemName())
    groups.setdefault((sku,footprint),[]).extend(refs);expected.update(refs)
with (PROD/'abx-motion-jlcpcb-bom.csv').open('w',newline='') as h:
    w=csv.writer(h);w.writerow(['Comment','Designator','Footprint','LCSC Part #'])
    for (sku,footprint),refs in sorted(groups.items(),key=lambda item:sorted(item[1])[0]):
        comment=comments[sku] if sku in comments else fs[refs[0]].GetValue()
        w.writerow([comment,','.join(sorted(refs)),footprint,sku])
cpl=list(csv.DictReader((PREV/'abx-motion-jlcpcb-cpl.csv').open()));previous={r['Designator']:dict(r) for r in cpl}
for r in cpl:
    if r['Designator'] in ['R2','R6']:r['Val']=fs[r['Designator']].GetValue()
    if r['Designator']=='D2':
        r.update({'Val':'TVS3300DRVR','Package':str(fs['D2'].GetFPID().GetLibItemName()),'Rotation':'180.0'})
for ref in ['R313','R413']:
    f=fs[ref];v=f.GetPosition()
    cpl.append({'Designator':ref,'Val':f.GetValue(),'Package':str(f.GetFPID().GetLibItemName()),
                'Mid X':f'{p.ToMM(v.x):.4f}mm','Mid Y':f'{-p.ToMM(v.y):.4f}mm',
                'Rotation':f'{f.GetOrientationDegrees()%360:.1f}','Layer':'Top'})
assert len(expected)==len(cpl)==239 and set(r['Designator'] for r in cpl)==expected
assert len(groups)==66
for row in cpl:
    ref=row['Designator']
    if ref in previous and ref not in ['D2','R2','R6']:assert row==previous[ref],ref
with (PROD/'abx-motion-jlcpcb-cpl.csv').open('w',newline='') as h:
    w=csv.DictWriter(h,fieldnames=list(cpl[0]));w.writeheader();w.writerows(cpl)

# Tolerance bounds: worst ADC divider gain uses high bottom / low top.
vbat_gain=(10000*1.01)/(150000*.99+10000*1.01)
cs_gain=1.01/(.99+1.01)
assert 47*vbat_gain<3.0
assert 5.5*cs_gain<3.0 # conservative SO bound above nominal AVDD, not its specified rating
audit={'decision':'Static checks pass; prototype fabrication candidate, pending assembler pin/polarity approval. Battery/load operation requires hardware validation.',
    'PCB_sha256':hashlib.sha256((ROOT/'abx-motion.kicad_pcb').read_bytes()).hexdigest(),
    'ERC_violations':0,'DRC_errors':0,'DRC_warnings':19,'unconnected_items':0,'schematic_parity':0,
    'schematic_pins_matched_to_PCB':len(pn),'functional_net_checks':len(checks),'functional_checks':checks,
    'all_original_tracks_and_vias_preserved':True,'original_track_and_via_count':len(ots),
    'added_tracks_and_vias':len(ts)-len(ots),'all_original_pads_preserved_except_D2':True,
    'all_original_component_locations_preserved':True,'all_other_footprints_including_logos_identical':True,
    'added_components':['R313','R413'],
    'BOM_groups':len(groups),'placements':len(cpl),'all_unchanged_CPL_rows_preserved':True,
    'In1_signal_tracks':0,'board_settings_unchanged':True,
    'nominal_VBAT_ADC_at_32V':32/16,'nominal_VBAT_ADC_at_40V':40/16,
    'VBAT_ADC_at_47V_worst_1_percent_resistors':47*vbat_gain,
    'CS_ADC_at_conservative_5_5V_SO_worst_1_percent_resistors':5.5*cs_gain,
    'R6_nominal_loss_at_32V_2_1V_LED_W':(32-2.1)**2/22000,
    'new_clamp_standoff_V':33,'new_clamp_max_V_at_specified_8_20us_pulse':40,
    'clamp_max_8_20us_A':35,'clamp_DRV_package_max_10_1000us_A':3.5,
    'new_clamp_supplier_CAD_rotation_verified':False,
    'assembly_action':'D2 pin 1 must be at board lower-right in top view (x182.975,y64.15). Confirm physical pin-1 dot in JLC editor; 180 degree CPL is provisional until that visual check.',
    'limits':'No continuous braking-energy rating. No measured continuous-current/thermal qualification. Not arbitrary StepStick compatibility.'}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps({k:v for k,v in audit.items() if k not in ['functional_checks']},indent=2))
