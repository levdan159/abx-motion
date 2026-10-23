"""Bounded placement-only delta. Writes only the ETH draft, never root PCB/copper.
Run once against 9f90d95 candidate; subsequent trials use the saved before file.
"""
from pathlib import Path
import pcbnew, ast, json, re, hashlib, shutil, math, subprocess
from shapely.geometry import LineString, box
from shapely.ops import polygonize, unary_union
R=Path(__file__).resolve().parents[2];A=Path(__file__).resolve().parent;O=R/'variants/ABX-Motion-ETH';P=O/'abx-motion-eth-placement.kicad_pcb'
mm=lambda x,y:pcbnew.VECTOR2I(round(x*1e6),round(y*1e6))
# Official TI RPE0009B land pattern: notably the upper/lower corner lands differ.
lib=O/'ethernet-footprints.pretty';lib.mkdir(exist_ok=True)
text=['(footprint "LMR36506_RPE0009B" (version 20241229) (generator "abx-ti-drawing") (layer "F.Cu")',
 '(descr "TI RPE0009B 2x2mm, drawing 4227033/B, datasheet Rev C p45; paste polygons 90% corner / 85% GND area, stencil release review required")',
 '(attr smd)',
 '(property "Reference" "REF**" (at 0 -1.8) (layer "F.SilkS") (effects (font (size .6 .6) (thickness .1))))',
 '(property "Value" "LMR36506R3RPER" (at 0 1.8) (layer "F.Fab") (effects (font (size .6 .6) (thickness .1))))']
def line(p,q,layer,width):text.append(f'(fp_line (start {p[0]} {p[1]}) (end {q[0]} {q[1]}) (stroke (width {width}) (type solid)) (layer "{layer}"))')
for lim,layer,w in [(1,'F.Fab',.1),(1.45,'F.CrtYd',.05)]:
 pts=[(-lim,-lim),(lim,-lim),(lim,lim),(-lim,lim)]
 for p,q in zip(pts,pts[1:]+pts[:1]):line(p,q,layer,w)
text.append('(fp_circle (center -1.12 -1.45) (end -.99 -1.45) (stroke (width .1) (type solid)) (fill none) (layer "F.SilkS"))')
top=[(-1.2,-.85),(-.85,-.85),(-.85,-1.2),(-.45,-1.2),(-.45,-.625),(-1.2,-.625)]
bottom=[(-1.2,.625),(-.5,.625),(-.5,1.2),(-.85,1.2),(-.85,.85),(-1.2,.85)]
for n,x,y,poly in [(1,-.9,-.7375,top),(8,.9,-.7375,[(-x,y) for x,y in top]),(4,-.9,.7375,bottom),(5,.9,.7375,[(-x,y) for x,y in bottom])]:
 pts=' '.join(f'(xy {px-x:.6f} {py-y:.6f})' for px,py in poly)
 text.append(f'(pad "{n}" smd custom (at {x} {y}) (size .2 .2) (layers "F.Cu" "F.Mask") (solder_mask_margin .025) (options (clearance outline) (anchor circle)) (primitives (gr_poly (pts {pts}) (width 0) (fill yes))))')
 # Uniform geometric scaling about polygon centroid gives exactly 90% area.
 from shapely.geometry import Polygon
 c=Polygon(poly).centroid;s=math.sqrt(.9)
 pp=' '.join(f'(xy {c.x+(px-c.x)*s:.6f} {c.y+(py-c.y)*s:.6f})' for px,py in poly)
 text.append(f'(fp_poly (pts {pp}) (stroke (width 0) (type solid)) (fill solid) (layer "F.Paste"))')
for n,x,y in [(2,-.9,-.25),(3,-.9,.25),(7,.9,-.25),(6,.9,.25)]:
 text.append(f'(pad "{n}" smd roundrect (at {x} {y}) (size .6 .25) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio .2) (solder_mask_margin .025))')
text.append('(pad "9" smd roundrect (at 0 -.55) (size .35 1.3) (layers "F.Cu" "F.Mask") (roundrect_rratio .142857) (solder_mask_margin .025))')
s=math.sqrt(.85);w=.35*s/2;h=1.3*s/2
text.append(f'(fp_rect (start {-w:.6f} {-.55-h:.6f}) (end {w:.6f} {-.55+h:.6f}) (stroke (width 0) (type solid)) (fill solid) (layer "F.Paste"))')
text.append('(model "${KIPRJMOD}/models/LMR36506-RPE-envelope.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n)')
(lib/'LMR36506_RPE0009B.kicad_mod').write_text('\n'.join(text)+'\n')
(O/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "abx-eth")(type "KiCad")(uri "${KIPRJMOD}/ethernet-footprints.pretty")(options "")(descr "ETH draft TI RPE footprint")))\n')
(O/'models/LMR36506-RPE-envelope.wrl').write_text('#VRML V2.0 utf8\n# Dimension envelope only, 2x2x1mm; not supplier CAD/CPL authority\nTransform { translation 0 0 0.1968504 children [Shape {appearance Appearance {material Material {diffuseColor .12 .12 .12}} geometry Box {size .7874016 .7874016 .3937008}}]}\n')
if not (A/'before.kicad_pcb').exists():(A/'before.kicad_pcb').write_bytes(subprocess.check_output(['git','show','9f90d95:variants/ABX-Motion-ETH/abx-motion-eth-placement.kicad_pcb'],cwd=R))
raw=(A/'before.kicad_pcb').read_text(); b=pcbnew.LoadBoard(str(A/'before.kicad_pcb'));fs={f.GetReference():f for f in b.GetFootprints()}
if not (A/'parts-before.json').exists():(A/'parts-before.json').write_bytes(subprocess.check_output(['git','show','9f90d95:variants/ABX-Motion-ETH/layout-review/parts.json'],cwd=R))
parts=json.loads((A/'parts-before.json').read_text());changed=set();added=set();removed=[]
plugin=pcbnew.GetPluginForPath(str(lib))
def add(ref,value,fp,x,y,ang=0,role='',mpn='',jlc=''):
 libname,name=fp.split(':');path=lib if libname=='abx-eth' else Path('/usr/share/kicad/footprints')/(libname+'.pretty')
 f=plugin.FootprintLoad(str(path),name,False);assert f,fp
 f.SetFPID(pcbnew.LIB_ID(libname,name));f.SetReference(ref);f.SetValue(value)
 f.Reference().SetVisible(ref in ['U802','U803','U804','L801']);f.Reference().SetTextSize(mm(.6,.6));f.Reference().SetTextThickness(100000)
 f.Value().SetVisible(False);f.SetOrientationDegrees(ang);f.SetPosition(mm(x,y));f.SetExcludedFromBOM(True);f.SetExcludedFromPosFiles(True)
 for p in f.Pads():p.SetNetCode(0)
 if ref in fs:removed.append(fs[ref]);changed.add(ref)
 else:added.add(ref)
 b.Add(f);fs[ref]=f
 parts[ref]=dict(value=value,footprint=fp,position=[x,y,ang],role=role,mpn=mpn,jlc=jlc,status=('selected component' if mpn else 'package/value selected; sourcing pending')+'; placement only; schematic/net integration pending',excluded_from_bom=True,excluded_from_cpl=True)
 return f
def move(ref,x,y,ang=None):
 f=fs[ref];f.SetPosition(mm(x,y))
 if ang is not None:f.SetOrientationDegrees(ang)
 changed.add(ref);parts[ref]['position']=[x,y,f.GetOrientationDegrees()]
 return f
C=lambda n,v,x,y,a=0,size='0603',role='',mpn='',jlc='':add('C'+str(n),v,'Capacitor_SMD:'+{'0402':'C_0402_1005Metric','0603':'C_0603_1608Metric','1206':'C_1206_3216Metric'}[size],x,y,a,role,mpn,jlc)
RR=lambda n,v,x,y,a=0,role='':add('R'+str(n),v,'Resistor_SMD:R_0402_1005Metric',x,y,a,role)
add('U802','LMR36506R3RPER','abx-eth:LMR36506_RPE0009B',145.5,56.35,180,'65V fixed3V3 600mA buck; Ethernet allocation 300mA; RT to VCC for1MHz','LMR36506R3RPER','C3190188')
add('L801','15uH / SWPA4030S150MT','Inductor_SMD:L_Sunlord_SWPA4030S',140,56.3,0,'15uH shielded output inductor; 1.11A RMS / 1.65A Isat; 3mm height','SWPA4030S150MT','C83475')
m=pcbnew.FP_3DMODEL();m.m_Filename='${KICAD9_3DMODEL_DIR}/Inductor_SMD.3dshapes/L_Sunlord_SWPA4030S.step';fs['L801'].Add3DModel(m)
for n,x in [(821,151),(822,153.7)]:C(n,'4.7uF 50V X7R',x,56.25,270,'1206','protected VBAT input bulk; verify combined effective capacitance >=2.2uF at32V','1206B475K500NT','C29823')
C(823,'100nF 50V X7R',146.8,54.1,0,'0603','input high frequency capacitor above U802; pad2 VIN, pad1 GND; front GND spine through center land','CC0603KRX7R9BB104','C14663')
C(824,'100nF 16V X7R',143.4,55.4,90,'0402','bootstrap capacitor; BOOT to SW, shortest local path','CL05B104KO5NNNC','C1525')
C(825,'1uF 25V X5R',143.4,57.6,270,'0402','internal VCC bypass; pad1 VCC, pad2 GND','CL05A105KA5NQNC','C52923')
for n,x in [(826,133.9),(827,136.4)]:C(n,'22uF 25V X5R',x,56.25,90,'1206','3V3_ETH output bulk; pad1 GND, pad2 output','CL31A226KAHNNNE','C12891')
RR(817,'10k',148,56.4,0,'main3V3 to EN series; follows main logic presence')
RR(818,'100k',148.2,58.55,0,'EN pull-down to ground')
move('TP_ETH_3V3',157,56.25)
# Moved only new draft parts to form a distinct SPI / reset island.
add('U804','TXU0304PWR','Package_SO:TSSOP-14_4.4x5mm_P0.65mm',110.3,82,0,'3 forward /1 return SPI isolator; Ioff; OE only while Ethernet selected','TXU0304PWR','C4364118')
move('C801',121.55,68.5,0)
move('C802',118.7,69,0)
move('C809',113.5,77.25,0);move('C810',114.1,78.5,0);move('C813',116.6,82.6,90)
move('Y801',119.4,82.5,0)
move('C807',122.6,81,0)
move('R808',123.7,82.3,0)
move('C814',122.1,83.3,90)
C(828,'100nF',107.4,78.2,0,'0402','U804 VCCA main3V3 bypass','CL05B104KO5NNNC','C1525')
C(829,'100nF',111.3,78.6,0,'0402','U804 VCCB Ethernet3V3 bypass','CL05B104KO5NNNC','C1525')
add('U803','TPS3808G33DBVR','Package_TO_SOT_SMD:SOT-23-6',112,88.5,180,'3.07V supervisor, CT open gives20ms delay; MR low from Q801','TPS3808G33DBVR','C43698')
add('Q801','BSS138','Package_TO_SOT_SMD:SOT-23',112,93,0,'MCU-expander-controlled open drain supervisor MR; no supply backfeed','BSS138','C52895')
move('C819',109.1,88.5,90)
move('R816',109,93,90)
move('R810',115.5,89.6,90)
move('R809',116.4,84.9,0)
move('R813',115.5,81.1,90);move('R814',115.5,83.3,90);move('R815',104.8,83.1,0)
add('Q802','BSS138','Package_TO_SOT_SMD:SOT-23',104,80,0,'CS inverter for OE; gate main CS_N, drain OE, source ground','BSS138','C52895')
RR(819,'10k',115.6,91.3,0,'supervisor MR pull-up to3V3_ETH; Q801 drain at MR')
RR(820,'4.7k',109.5,85.5,0,'SPI OE pull-up to main3V3; Q802 clamps low when deselected')
RR(821,'10k',103.9,77.1,0,'MCU Ethernet CS_N pull-up to main3V3; boot strap must be validated')
# Replace only the old reservation object with smaller functional documentation.
removed.append(fs['PWR_ETH_RESERVE'])
for f in removed:b.Remove(f)
labels=[]
for content,x,y in [('3V3_ETH',157,58.45),('ETH SPI',110.3,75.3),('ETH RESET',112,95.5)]:
 t=pcbnew.PCB_TEXT(b);t.SetText(content);t.SetPosition(mm(x,y));t.SetTextSize(mm(.6,.6));t.SetTextThickness(100000);t.SetLayer(pcbnew.F_SilkS if content=='3V3_ETH' else pcbnew.Dwgs_User);b.Add(t);labels.append(t.m_Uuid.AsString())
# Move old test point label; delete old reserve title if attached to board text.
label_removed=[]
for t in list(b.GetDrawings()):
 if t.GetClass()=='PCB_TEXT' and t.GetText()=='3V3_ETH' and t.m_Uuid.AsString() not in labels:
  label_removed.append(t.m_Uuid.AsString());b.Remove(t)
# Recreate functional outline on Dwgs.User (not a copper keepout).
for p,q in [((132.6,53.3),(158.5,53.3)),((158.5,53.3),(158.5,59.35)),((158.5,59.35),(132.6,59.35)),((132.6,59.35),(132.6,53.3))]:
 g=pcbnew.PCB_SHAPE();g.SetShape(pcbnew.SHAPE_T_SEGMENT);g.SetStart(mm(*p));g.SetEnd(mm(*q));g.SetLayer(pcbnew.Dwgs_User);g.SetWidth(100000);b.Add(g);labels.append(g.m_Uuid.AsString())
# Pure helpers only: avoid running the legacy full-board generator.
ns={};tree=ast.parse((R/'work/ethernet-rev1.2b-20261023/placement.py').read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='blocks'],type_ignores=[]),'blocks','exec'),ns);blocks=ns['blocks']
ns=globals();tree=ast.parse((R/'work/ethernet-rev1.2b-20261023/review.py').read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['outline','bounds']],type_ignores=[]),'geometry','exec'),ns)
polys={r:bounds(f) for r,f in fs.items() if r not in ['LOGO1','LOGO2','PWR_ETH_RESERVE']}
hits=[]
for r in changed|added:
 for s,p in polys.items():
  if s==r or (s in changed|added and s<r):continue
  inter=polys[r].intersection(p)
  if inter.area>.0001:hits.append(dict(a=r,b=s,area=round(inter.area,5)))
(A/'trial-overlaps.json').write_text(json.dumps(hits,indent=2)+'\n')
print('Footprints',len(parts),'new',len(added),'changed',len(changed),'overlaps',len(hits));print(json.dumps(hits,indent=1))
# Native output is only a source of selected footprint/drawing expressions.
native=A/'native.kicad_pcb';pcbnew.SaveBoard(str(native),b)
if hits:raise SystemExit('Placement geometry failed; candidate not changed.')
ref=lambda s:re.search(r'\(property "Reference" "([^"]+)"',s)[1]
uid=lambda s:re.search(r'\(uuid "([^"]+)"',s)[1]
old=blocks(raw);new=blocks(native.read_text());nf={ref(s):s for _,_,s in new if s.startswith('(footprint ')}
for lo,hi,s in reversed(old):
 if s.startswith('(footprint ') and ref(s) in changed:raw=raw[:lo]+nf[ref(s)]+raw[hi:]
 elif s.startswith('(footprint ') and ref(s)=='PWR_ETH_RESERVE':raw=raw[:lo].rstrip(' \t')+raw[hi:]
 elif s.startswith('(gr_text ') and uid(s) in label_removed:raw=raw[:lo].rstrip(' \t')+raw[hi:]
extra=[nf[r] for r in sorted(added)]+[s for _,_,s in new if (s.startswith('(gr_text ') or s.startswith('(gr_line ')) and uid(s) in labels]
i=raw.rfind('\n)');raw=raw[:i]+'\n\t'+'\n\t'.join(extra)+raw[i:]
after=blocks(raw)
copper=lambda bl:[s for _,_,s in bl if re.match(r'^\((?:segment|via|zone)\s',s)]
assert copper(old)==copper(after),'Existing copper changed!'
off={ref(s):s for _,_,s in old if s.startswith('(footprint ')};aff={ref(s):s for _,_,s in after if s.startswith('(footprint ')}
actual_changed={r for r in off if r in aff and off[r]!=aff[r]};assert actual_changed==changed
assert set(off)-set(aff)=={'PWR_ETH_RESERVE'}
P.write_text(raw);(O/'layout-review/parts.json').write_text(json.dumps(parts,indent=2)+'\n')
proof=dict(date='2026-10-24',stage='placement only',source_pcb_sha256=hashlib.sha256((R/'abx-motion.kicad_pcb').read_bytes()).hexdigest(),draft_before_sha256=hashlib.sha256((A/'before.kicad_pcb').read_bytes()).hexdigest(),draft_after_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),existing_segments_vias_zones_preserved_verbatim=True,existing_footprints_preserved_verbatim_except_listed_new_draft_parts=sorted(changed),added_footprints=sorted(added),removed_footprints=['PWR_ETH_RESERVE'],all_new_footprints_excluded_from_bom_and_cpl=True,new_pads_unconnected=True,zero_courtyard_overlaps=True)
(O/'layout-review/ethernet-supply-placement.json').write_text(json.dumps(proof,indent=2)+'\n')
print('Saved bounded ETH placement delta; original copper and all existing Rev1.2a positions unchanged.')
