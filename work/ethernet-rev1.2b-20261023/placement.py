"""Build a placement-only review board. Never writes the root PCB or schematics."""
from pathlib import Path
import pcbnew, json, uuid, re, hashlib, math, subprocess

R=Path(__file__).resolve().parents[2]
A=R/'work/ethernet-rev1.2b-20261023'
O=R/'variants/ABX-Motion-ETH'
O.mkdir(exist_ok=True)
if not (A/'before/abx-motion.kicad_pcb').exists():
 (A/'before').mkdir(parents=True,exist_ok=True)
 (A/'before/abx-motion.kicad_pcb').write_bytes(subprocess.check_output(['git','show','ce34a43:abx-motion.kicad_pcb'],cwd=R))
before=(A/'before/abx-motion.kicad_pcb').read_text()
b=pcbnew.LoadBoard(str(A/'before/abx-motion.kicad_pcb'))
fs={f.GetReference():f for f in b.GetFootprints()}
mm=lambda x,y:pcbnew.VECTOR2I(round(x*1e6),round(y*1e6))

# Restricted local placement changes. Copper is retained verbatim in the review
# board so a placement experiment cannot erase necessary original connections.
moves={
 # Five rail/ground pads right of RJ45; CS1/CS2 left of ESP32.
 'TP_BATT1':(132.5,51,0), 'TP_5V1':(138,51,0),
 'TP_3V3_1':(143.5,51,0), 'TP_GND1':(149,51,0),
 'TP_GND2':(154.5,51,0), 'TP_CS1':(82.5,51,90),
 'TP_CS2':(88,51,90),
 # Frees the original small logic pull-up row beneath the new PHY.
 'R747':(134.5,82.5,0), 'R748':(132.5,86,0), 'R749':(132.5,88.2,0),
}
moved=[]
for ref,(x,y,ang) in moves.items():
 f=fs[ref];p=f.GetPosition();old=[p.x/1e6,p.y/1e6,f.GetOrientationDegrees()]
 f.SetOrientationDegrees(ang);f.SetPosition(mm(x,y))
 moved.append(dict(ref=ref,before=old,after=[x,y,ang]))

parts={}
def add(ref,value,fp,x,y,ang=0,role='',status='reference-circuit placement; electrical integration pending'):
 lib,name=fp.split(':');f=pcbnew.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',name)
 assert f,fp
 f.SetFPID(pcbnew.LIB_ID(lib,name));f.SetReference(ref);f.SetValue(value)
 f.Reference().SetVisible(ref in ['U801','J801','Y801']);f.Reference().SetTextSize(mm(.65,.65));f.Reference().SetTextThickness(100000)
 f.Value().SetVisible(False);f.SetOrientationDegrees(ang);f.SetPosition(mm(x,y))
 f.SetExcludedFromBOM(True);f.SetExcludedFromPosFiles(True)
 # No invented electrical connectivity in this placement-only board.
 for p in f.Pads():p.SetNetCode(0)
 b.Add(f);fs[ref]=f
 parts[ref]=dict(value=value,footprint=fp,position=[x,y,ang],role=role,status=status,
                 excluded_from_bom=True,excluded_from_cpl=True)
 return f

add('J801','HR911105A / C12074','Connector_RJ:RJ45_Hanrun_HR911105A_Horizontal',125,63.25,180,'RJ45 opening toward the top edge; extra antenna clearance waived by user')
# Locally authored dimensional envelope: visualization only, not a supplier CAD
# model or assembly-orientation authority. VRML uses 2.54 mm units in KiCad.
model=O/'models/HR911105A-envelope.wrl';model.parent.mkdir(exist_ok=True)
vr=['#VRML V2.0 utf8','# HR911105A approximate mechanical envelope; 2.54 mm units; not supplier CAD']
def solid(x,y,z,dx,dy,dz,color):
 vals=[v/2.54 for v in (x,-y,z,dx,dy,dz)]
 vr.append('Transform { translation %.6f %.6f %.6f children [ Shape { appearance Appearance { material Material { diffuseColor %s } } geometry Box { size %.6f %.6f %.6f } } ] }'%(*vals[:3],color,*vals[3:]))
# Body matches the footprint's F.Fab XY outline, mouth at local +Y.
solid(4.44,2.2,6.75,16.04,12.48,13.5,'.55 .58 .60')
solid(-3.28,12.85,6.75,.6,8.82,13.5,'.65 .68 .7')
solid(12.16,12.85,6.75,.6,8.82,13.5,'.65 .68 .7')
solid(4.44,12.85,13.2,14.84,8.82,.6,'.65 .68 .7')
solid(4.44,12.85,.6,14.84,8.82,1.2,'.65 .68 .7')
solid(4.44,8.5,6.4,14.84,.2,10.4,'.045 .045 .045')
solid(-1.0,17,2.1,2.3,.52,1.2,'.05 .6 .12')
solid(9.8,17,2.1,2.3,.52,1.2,'.95 .55 .03')
model.write_text('\n'.join(vr)+'\n')
fs['J801'].Models().clear();mod=pcbnew.FP_3DMODEL();mod.m_Filename='${KIPRJMOD}/models/HR911105A-envelope.wrl';fs['J801'].Add3DModel(mod)
add('U801','W5500 / C32843','Package_QFP:LQFP-48_7x7mm_P0.5mm',120.3,74.8,270,'integrated 10/100 MAC and PHY; MDI pins toward jack')
add('Y801','25MHz / CL TO SELECT','Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',119.8,82,0,'crystal; exact CL and drive specification pending')

def cap(n,v,x,y,ang=0,role='',size='0402'):
 fp={'0402':'C_0402_1005Metric','0603':'C_0603_1608Metric','0805':'C_0805_2012Metric','1206':'C_1206_3216Metric'}[size]
 return add('C'+str(n),v,'Capacitor_SMD:'+fp,x,y,ang,role)
def res(n,v,x,y,ang=0,role='',size='0402'):
 fp='R_0402_1005Metric' if size=='0402' else 'R_0603_1608Metric'
 return add('R'+str(n),v,'Resistor_SMD:'+fp,x,y,ang,role)

# Per-pin bypass positions are reviewed against the rotated W5500 pin bank.
for n,x,y,ang in [(801,121.75,69,0),(802,119.25,69,0),
 (803,116.75,69,0),(804,114,71.6,0),
 (805,114,73.7,0),(806,114,76,0),(807,123.8,80.5,0)]:
 cap(n,'100nF',x,y,ang,'local W5500 supply bypass')
# W5500 pin 18 VBG must float. TOCAP (20) needs 4.7uF; 1V2O (22) needs 10nF.
cap(809,'4.7uF',112.1,77,90,'TOCAP capacitor; pin 20',size='0603')
cap(810,'10nF',114,78.8,90,'1V2O capacitor; pin 22')
cap(811,'10uF',126.5,82.6,0,'digital supply bulk',size='0805')
cap(812,'10uF',130,82.5,0,'analog supply bulk',size='0805')
cap(813,'CL TBD',116.4,80.5,0,'crystal load capacitor')
cap(814,'CL TBD',123.5,83.3,0,'crystal load capacitor')
cap(815,'100nF',129.15,68.7,0,'TX center-tap bypass; confirm jack pin mapping')
cap(816,'10nF',129,70.5,0,'RX center-tap network; confirm jack topology')
cap(817,'6.8nF',129,78,0,'RX reference termination network')
cap(818,'6.8nF',129,80,0,'RX reference termination network')
res(801,'12.4k 1%',114.5,69.1,0,'EXRES1 bias resistor')
for n,y in [(802,71.2),(803,73.2),(804,75.2),(805,77.2)]:
 res(n,'49.9R 1%',126.5,y,0,'MDI termination; final center-tap circuit review pending')
for n,x,y in [(806,126.5,79.1),(807,126.5,80.7),(808,123.6,81.8)]:res(n,'10k',x,y,0,'PMODE strap')
res(809,'10k',116.8,85.5,0,'CS pull-up')
res(810,'10k',117,89,0,'RESET pull-up')
res(811,'330R',130.4,54,90,'RJ45 green LED resistor')
res(812,'330R',130.4,56.5,90,'RJ45 yellow LED resistor')
res(813,'22R / SI TBD',113.7,91,0,'SPI series option')
res(814,'22R / SI TBD',113.7,93,0,'SPI series option')
res(815,'22R / SI TBD',113.7,95,0,'SPI series option')
add('FB801','FERRITE / RATED >=300mA','Inductor_SMD:L_0603_1608Metric',126.6,68.75,0,'analog supply filter')
add('U803','OPEN-DRAIN RESET / SELECT','Package_TO_SOT_SMD:SOT-23',114,84,0,'power-on reset supervisor; MPN not frozen')
cap(819,'100nF',111,83.7,0,'supervisor bypass')
add('Q801','RESET SINK / SELECT','Package_TO_SOT_SMD:SOT-23',113,87.5,0,'expander reset open-drain interface')
res(816,'100k',111.5,89.7,0,'reset interface default state')
add('D801','ETHERNET ESD / SELECT','Package_TO_SOT_SMD:SOT-23-6',130,74.4,0,'low capacitance Ethernet protection; MPN/topology not frozen')
cap(820,'1nF HV / SELECT',134.5,59.8,0,'shield coupling position; voltage/clearance review pending',size='1206')
add('TP_ETH_3V3','3V3_ETH / UNCONNECTED DRAFT','TestPoint:TestPoint_Pad_D1.5mm',133.5,56.25,0,'intended 3V3_ETH measurement point; schematic/net assignment pending')

# A dimensioned reservation rather than an invented regulator footprint. The
# dedicated rail must not silently consume the old 1 A external 5 V allocation.
reserve=pcbnew.FOOTPRINT(b);reserve.SetReference('PWR_ETH_RESERVE');reserve.SetValue('3V3 ETH SUPPLY - REVIEW');reserve.SetPosition(mm(143.5,56.25))
reserve.SetExcludedFromBOM(True);reserve.SetExcludedFromPosFiles(True)
reserve.Reference().SetVisible(False);reserve.Value().SetVisible(False)
for p,q in [((-12.5,-2.25),(12.5,-2.25)),((12.5,-2.25),(12.5,2.25)),((12.5,2.25),(-12.5,2.25)),((-12.5,2.25),(-12.5,-2.25))]:
 s=pcbnew.PCB_SHAPE(reserve);s.SetShape(pcbnew.SHAPE_T_SEGMENT);s.SetStart(mm(143.5+p[0],56.25+p[1]));s.SetEnd(mm(143.5+q[0],56.25+q[1]));s.SetLayer(pcbnew.Dwgs_User);s.SetWidth(150000);reserve.Add(s)
b.Add(reserve)

def text(s,x,y,size=.8,layer=pcbnew.Dwgs_User):
 t=pcbnew.PCB_TEXT(b);t.SetText(s);t.SetPosition(mm(x,y));t.SetTextSize(mm(size,size));t.SetTextThickness(120000);t.SetLayer(layer);b.Add(t)
text('3V3 ETH SUPPLY RESERVE',147.75,56.25,.65)
text('3V3_ETH',133.5,54.4,.65,pcbnew.F_SilkS)
text('ETHERNET - PLACEMENT REVIEW ONLY',131,44.5,1)
text('NO PoE',120.6,47,.65)
text('EXTRA ANTENNA CLEARANCE WAIVED - WIFI TEST REQUIRED',125,40.8,.7)
text('PHY',120.3,74.8,.8)
text('Copper retained from Rev 1.2a; moved pads are NOT rerouted.\nNew footprints are excluded from BOM/CPL and not schematic-integrated.',128,36,.85)
text('ETH',120.6,68.4,.8,pcbnew.F_SilkS)

# Rev/SKU changes are confined to the candidate. Existing netlist remains 1.2a.
b.GetTitleBlock().SetRevision('1.2b PLACEMENT DRAFT')
label_refs={'+BATT':'TP_BATT1','+5V':'TP_5V1','+3V3':'TP_3V3_1','GND1':'TP_GND1','GND2':'TP_GND2','CS1':'TP_CS1','CS2':'TP_CS2'}
changedtexts=set()
for d in b.GetDrawings():
 if d.GetClass()=='PCB_TEXT':
  s=d.GetText()
  if 'ABX-Motion Rev 1.2a' in s:
   d.SetText(s.replace('ABX-Motion Rev 1.2a','ABX-Motion Rev 1.2b'));changedtexts.add(d.m_Uuid.AsString())
  p=d.GetPosition()
  if s in label_refs and abs(p.y/1e6-53.5)<.01 and 112<p.x/1e6<151:
   x,y,_=moves[label_refs[s]];ly=48.55 if y<53 else 53.65 if y<60 else 62
   d.SetPosition(mm(x,ly));d.SetTextSize(mm(.6,.6));d.SetTextThickness(100000);changedtexts.add(d.m_Uuid.AsString())

tmp=A/'native-candidate.kicad_pcb';pcbnew.SaveBoard(str(tmp),b)

def blocks(s):
 out=[];dep=0;quoted=False;esc=False;start=None
 for i,c in enumerate(s):
  if quoted:
   if esc:esc=False
   elif c=='\\':esc=True
   elif c=='"':quoted=False
   continue
  if c=='"':quoted=True;continue
  if c=='(':
   if dep==1:start=i
   dep+=1
  elif c==')':
   dep-=1
   if dep==1 and start is not None:out.append((start,i+1,s[start:i+1]));start=None
 return out

# Native SaveBoard can update filled-zone/net data. Keep every original copper
# expression byte-for-byte, taking only intended footprint/text blocks from it.
nb=blocks(tmp.read_text());ob=blocks(before)
keyref=lambda s:re.search(r'\(property "Reference" "([^"]+)"',s)[1]
newfps={keyref(s):s for _,_,s in nb if s.startswith('(footprint ')}
newtexts={re.search(r'\(uuid "([^"]+)"',s)[1]:s for _,_,s in nb if s.startswith('(gr_text ')}
oldtextids={re.search(r'\(uuid "([^"]+)"',s)[1] for _,_,s in ob if s.startswith('(gr_text ')}
raw=before
for lo,hi,s in reversed(ob):
 if s.startswith('(footprint ') and keyref(s) in moves:raw=raw[:lo]+newfps[keyref(s)]+raw[hi:]
 elif s.startswith('(gr_text '):
  u=re.search(r'\(uuid "([^"]+)"',s)[1]
  if u in changedtexts:raw=raw[:lo]+newtexts[u]+raw[hi:]
 elif s.startswith('(title_block'):raw=raw[:lo]+s.replace('1.2a','1.2b PLACEMENT DRAFT')+raw[hi:]
extra=[newfps[r] for r in parts]+[newfps['PWR_ETH_RESERVE']]+[s for u,s in newtexts.items() if u not in oldtextids]
i=raw.rfind('\n)');raw=raw[:i]+''.join('\n\t'+s for s in extra)+raw[i:]
out=O/'abx-motion-eth-placement.kicad_pcb';out.write_text(raw)

# Exact preservation evidence for old copper and stationary footprint placement.
afterblocks=blocks(raw)
oldfps={keyref(s):s for _,_,s in ob if s.startswith('(footprint ')}
afterfps={keyref(s):s for _,_,s in afterblocks if s.startswith('(footprint ')}
for ref,s in oldfps.items():
 if ref not in moves:assert afterfps[ref]==s,('stationary footprint changed',ref)
types=('segment','via','zone')
for t in types:
 a=[s for _,_,s in ob if s.startswith('('+t+'\n') or s.startswith('('+t+' ')]
 z=[s for _,_,s in blocks(raw) if s.startswith('('+t+'\n') or s.startswith('('+t+' ')]
 assert a==z,t
(O/'layout-review/parts.json').write_text(json.dumps(parts,indent=2))
(O/'layout-review/moved-parts.json').write_text(json.dumps(moved,indent=2))
(O/'layout-review/preservation.json').write_text(json.dumps(dict(
 baseline_commit='ce34a43',root_pcb_unchanged=hashlib.sha256((R/'abx-motion.kicad_pcb').read_bytes()).hexdigest()==hashlib.sha256((A/'before/abx-motion.kicad_pcb').read_bytes()).hexdigest(),
 original_copper_preserved_verbatim=True,stationary_footprints_preserved_verbatim=True,
 existing_supply_placement_unchanged=True,new_footprints=len(parts),moved_existing=len(moves),
 new_electrical_connections=0,stage='placement only; not for manufacture'),indent=2))
print('Saved',out,'new footprints',len(parts),'moved existing',len(moves))
