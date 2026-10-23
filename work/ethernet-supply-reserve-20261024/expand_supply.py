"""Apply only the expanded supply reservation and unconnected probe-pad draft."""
from pathlib import Path
import ast, hashlib, json, re, shutil
import pcbnew

R=Path(__file__).resolve().parents[2]
A=Path(__file__).resolve().parent
O=R/'variants/ABX-Motion-ETH'
P=O/'abx-motion-eth-placement.kicad_pcb'
raw=P.read_text()
shutil.copy2(P,A/'before.kicad_pcb')
env={}
tree=ast.parse((R/'work/ethernet-rev1.2b-20261023/placement.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='blocks'],type_ignores=[]),'blocks','exec'),env)
blocks=env['blocks'];old=blocks(raw)
keyref=lambda s:re.search(r'\(property "Reference" "([^"]+)"',s)[1]
uid=lambda s:re.search(r'\(uuid "([^"]+)"',s)[1]
mm=lambda x,y:pcbnew.VECTOR2I(round(x*1e6),round(y*1e6))
b=pcbnew.LoadBoard(str(P));fs={f.GetReference():f for f in b.GetFootprints()}
assert 'TP_ETH_3V3' not in fs,'Already applied; do not regenerate unrelated objects.'
reserve=fs['PWR_ETH_RESERVE'];reserve.SetPosition(mm(143.5,56.25))
edges=[((131,54),(156,54)),((156,54),(156,58.5)),((156,58.5),(131,58.5)),((131,58.5),(131,54))]
graphics=list(reserve.GraphicalItems());assert len(graphics)==4
for g,(p,q) in zip(graphics,edges):g.SetStart(mm(*p));g.SetEnd(mm(*q))

ref='TP_ETH_3V3';fp='TestPoint_Pad_D1.5mm'
f=pcbnew.FootprintLoad('/usr/share/kicad/footprints/TestPoint.pretty',fp)
assert f
f.SetFPID(pcbnew.LIB_ID('TestPoint',fp));f.SetReference(ref)
f.SetValue('3V3_ETH / UNCONNECTED DRAFT');f.SetPosition(mm(133.5,56.25))
f.Reference().SetVisible(False);f.Value().SetVisible(False)
f.SetExcludedFromBOM(True);f.SetExcludedFromPosFiles(True)
for pad in f.Pads():pad.SetNetCode(0)
b.Add(f)
t=pcbnew.PCB_TEXT(b);t.SetText('3V3_ETH');t.SetPosition(mm(133.5,54.4))
t.SetTextSize(mm(.65,.65));t.SetTextThickness(120000);t.SetLayer(pcbnew.F_SilkS);b.Add(t)
native=A/'native.kicad_pcb';pcbnew.SaveBoard(str(native),b)
nb=blocks(native.read_text());fps={keyref(s):s for _,_,s in nb if s.startswith('(footprint ')}
newlabel=next(s for _,_,s in nb if s.startswith('(gr_text ') and uid(s)==t.m_Uuid.AsString())
for lo,hi,s in reversed(old):
 if s.startswith('(footprint ') and keyref(s)=='PWR_ETH_RESERVE':raw=raw[:lo]+fps['PWR_ETH_RESERVE']+raw[hi:]
i=raw.rfind('\n)');raw=raw[:i]+'\n\t'+fps[ref]+'\n\t'+newlabel+raw[i:]
after=blocks(raw)
changed_old=[s for (_,_,s),(_,_,z) in zip(old,after) if s!=z]
assert len(changed_old)==1 and keyref(changed_old[0])=='PWR_ETH_RESERVE'
assert len(after)==len(old)+2
P.write_text(raw)
manifest=O/'layout-review/parts.json';parts=json.loads(manifest.read_text())
parts[ref]=dict(value=f.GetValue(),footprint='TestPoint:'+fp,position=[133.5,56.25,0],
 role='intended 3V3_ETH measurement point; schematic/net assignment pending',
 status='reference-circuit placement; electrical integration pending',
 excluded_from_bom=True,excluded_from_cpl=True)
manifest.write_text(json.dumps(parts,indent=2))
q=O/'layout-review/preservation.json';data=json.loads(q.read_text());data['new_footprints']=len(parts);q.write_text(json.dumps(data,indent=2))
proof=dict(date='2026-10-24',reservation_before_mm=[139.5,54,156,58.5],
 reservation_after_mm=[131,54,156,58.5],area_before_mm2=74.25,area_after_mm2=112.5,
 test_point=dict(reference=ref,position_mm=[133.5,56.25],diameter_mm=1.5,
                connected=False,excluded_from_bom=True,excluded_from_cpl=True),
 all_other_existing_board_objects_preserved_verbatim=True,
 segments_vias_zones_unchanged=True,existing_component_positions_unchanged=True,
 source_pcb_sha256=hashlib.sha256((R/'abx-motion.kicad_pcb').read_bytes()).hexdigest())
(O/'layout-review/supply-reservation-expansion.json').write_text(json.dumps(proof,indent=2)+'\n')
print('Expanded supply reservation to 25 x 4.5 mm and added unconnected 3V3_ETH probe-pad position.')
