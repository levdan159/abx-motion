"""Value-only current-limit change and revision markings; never routes or regenerates."""
from pathlib import Path
import shutil,re,json,csv,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
files=[ROOT/'abx-motion.kicad_pcb',*ROOT.glob('*.kicad_sch'),ROOT/'generate_schematics.py',ROOT/'README.md',ROOT/'abx-footprints.pretty/ABX_Text_Gold.kicad_mod',ROOT/'production/abx-motion-jlcpcb-bom.csv',ROOT/'production/abx-motion-jlcpcb-cpl.csv']
for f in files:
 dst=OUT/'before'/f.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists(),str(dst);shutil.copy2(f,dst)
def spans(s,tag):
 # Extract balanced native S-expressions, respecting quoted strings and escapes.
 for m in re.finditer(r'\('+tag+r'(?=\s)',s):
  i=m.start();depth=0;quoted=False;esc=False
  for j in range(i,len(s)):
   ch=s[j]
   if quoted:
    if esc:esc=False
    elif ch=='\\':esc=True
    elif ch=='"':quoted=False
   elif ch=='"':quoted=True
   elif ch=='(':depth+=1
   elif ch==')':
    depth-=1
    if depth==0:yield i,j+1,s[i:j+1];break
board=ROOT/'abx-motion.kicad_pcb';s=board.read_text();orig=s;edits=[]
for i,j,part in spans(s,'footprint'):
 if any(f'(property "Reference" "{ref}"' in part for ref in ['R302','R402']):
  assert '(property "Value" "30k"' in part and '(property "LCSC" "C22984"' in part
  edits.append((i,j,part.replace('(property "Value" "30k"','(property "Value" "12k"').replace('(property "LCSC" "C22984"','(property "LCSC" "C22790"')))
assert len(edits)==2
for i,j,part in reversed(edits):s=s[:i]+part+s[j:]
s=s.replace('Rev 1.1b','Rev 1.1c').replace('REV 1.1b','REV 1.1c').replace('(rev "1.1b")','(rev "1.1c")').replace('15A Chop','9.4A Chop')
# Strict byte-level invariant: undo ONLY the authorized value, SKU and text edits.
undo=s.replace('Rev 1.1c','Rev 1.1b').replace('REV 1.1c','REV 1.1b').replace('(rev "1.1c")','(rev "1.1b")').replace('9.4A Chop','15A Chop')
for i,j,part in reversed(list(spans(undo,'footprint'))):
 if any(f'(property "Reference" "{ref}"' in part for ref in ['R302','R402']):
  undo=undo[:i]+part.replace('(property "Value" "12k"','(property "Value" "30k"').replace('(property "LCSC" "C22790"','(property "LCSC" "C22984"')+undo[j:]
assert undo==orig
board.write_text(s)
for f in ROOT.glob('*.kicad_sch'):
 s=f.read_text().replace('(rev "1.1b")','(rev "1.1c")')
 if f.name=='Motor_Channel.kicad_sch':
  assert s.count('(property "Value" "30k"')==1;s=s.replace('(property "Value" "30k"','(property "Value" "12k"')
 f.write_text(s)
f=ROOT/'abx-footprints.pretty/ABX_Text_Gold.kicad_mod';f.write_text(f.read_text().replace('Rev 1.1b','Rev 1.1c'))
f=ROOT/'generate_schematics.py';s=f.read_text().replace('HARDWARE_REVISION = "1.1b"','HARDWARE_REVISION = "1.1c"')
s=s.replace('# VREF divider: R01 (18k to AVDD) and R02 (30k to GND) -> 3.0V (15A chop limit)','# VREF divider: R01 18k / R02 12k -> 1.92V, 9.35A nominal chopping (not a power limiter).')
old='r_vref_lo = sb.place_sym("Device:R", r, "30k",';new='r_vref_lo = sb.place_sym("Device:R", r, "12k",';assert old in s;s=s.replace(old,new);f.write_text(s)
f=ROOT/'README.md';s=f.read_text().replace('Rev 1.1b','Rev 1.1c').replace('rev-1.1b-20261020','rev-1.1c-20261020')
s=s.replace('revision 1.1b','revision 1.1c').replace('This revision includes the','Rev 1.1b included the')
s=s.replace('The revision-marking pass changes silkscreen and title metadata\nonly; it preserves the existing electrical layout.','Rev 1.1c additionally changes R302/R402 from 30k to 12k (C22790) to lower\nthe DC current-chopping target from 14.75 A to 9.35 A nominal. The checked\nstatic tolerance range is about 6.7–11.5 A, before blanking/propagation\novershoot. Layout and copper routing are unchanged. This may restrict torque\nfor low-voltage motors operated through PWM; it is not a 150 W power limiter.')
s += '\n## Motor robustness and bench acceptance\n\nDesign case: two DC motors, each drawing up to 150 W electrically for one\nsecond; 300 W combined excludes StepStick loads and other peripherals. This\nis a proposed intermittent operating envelope, not a measured board rating.\nMotor winding current can exceed battery current under PWM. Current chopping\ndoes not protect arbitrary low-inductance motors, brake-mode currents or a\nsustained short. DRV8701 retries faults automatically; its die-temperature\nshutdown does not measure the external MOSFETs or Q1.\n\nFollow `validation/robustness-final-20261020/bench-procedure.txt` at the intended\npack voltage with fault energy limited before connecting motors. No physical\nload, thermal, stall or regenerative test has yet been performed. Do not infer\nsafety from the 25 A holder label or 150 W motor power. Use actual phase-current\nmeasurements, a timed stop and a verified return-energy path during testing.\n'
f.write_text(s)
# Prepare BOM/CPL in the new candidate; preserve every placement coordinate/angle.
prod=ROOT/'production/rev-1.1c-20261020';prod.mkdir(exist_ok=True)
for name in ['abx-motion-jlcpcb-bom.csv','abx-motion-jlcpcb-cpl.csv']:
 rows=list(csv.DictReader(open(ROOT/'production'/name)));fields=list(rows[0]);changed=0
 for r in rows:
  if name.endswith('bom.csv') and set(r['Designator'].split(','))=={'R302','R402'}:
   assert r['Comment']=='30k' and r['LCSC Part #']=='C22984';r['Comment']='12k';r['LCSC Part #']='C22790';changed=2
  if name.endswith('cpl.csv') and r['Designator'] in ['R302','R402']:
   assert r['Val']=='30k';r['Val']='12k';changed+=1
 assert changed==2
 with open(prod/name,'w',newline='') as ff:w=csv.DictWriter(ff,fieldnames=fields);w.writeheader();w.writerows(rows)
(OUT/'changes.json').write_text(json.dumps({'revision':'1.1c','changed_values':{'R302':{'before':'30k C22984','after':'12k C22790'},'R402':{'before':'30k C22984','after':'12k C22790'}},'nominal_current_chop_A':9.35,'routing_pad_net_and_board_geometry_changes':0,'strict_byte_scope_check_passed':True,'second_TVS_added':False,'physical_tests_performed':False},indent=2)+'\n')
print('Applied R302/R402 12k; all routing, pads and net assignments preserved; marked Rev 1.1c.')
