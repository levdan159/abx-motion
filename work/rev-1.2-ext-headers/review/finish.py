from pathlib import Path
import pcbnew as p,sexpdata as sx,re
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;lib=R/'abx-footprints.pretty/EXT_Header_1x04_P2.54mm_RightAngle.kicad_mod'
tag=lambda x:str(x[0]) if isinstance(x,list) and x else ''
tree=sx.loads(lib.read_text())
for x in tree:
 if tag(x) not in ['fp_line','fp_rect','fp_poly']:continue
 layer=next((q for q in x if tag(q)=='layer'),None)
 if not layer or layer[1]!='F.SilkS':continue
 pts=[q for q in x if tag(q) in ['start','end','center','mid']]
 if pts and max(q[1] for q in pts)>4.16:layer[1]='F.Fab'
lib.write_text(sx.dumps(tree)+'\n')
b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'))
for f in b.GetFootprints():
 if f.GetReference() not in ['J502','J504']:continue
 f.SetField('Datasheet','https://www.we-online.com/components/products/datasheet/61300411021.pdf')
 for name in ['Manufacturer','MPN','Datasheet']:
  fld=f.GetField(name);fld.SetVisible(False);fld.SetLayer(p.F_Fab)
 for g in f.GraphicalItems():
  if g.GetLayer()==p.F_SilkS and g.GetBoundingBox().GetBottom()>p.FromMM(152.5):g.SetLayer(p.F_Fab)
p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b)
sch=R/'Steppers_Relays.kicad_sch';text=sch.read_text();starts=[m.start() for m in re.finditer(r'^\t\(symbol\n',text,re.M)]+[len(text)]
for a,z in reversed(list(zip(starts,starts[1:]))):
 block=text[a:z]
 if not any(f'(property "Reference" "{ref}"' in block for ref in ['J502','J504']):continue
 pos=re.search(r'\(property "Reference" "J50[24]"\s+\(at ([\d.]+) ([\d.]+)',block);x,y=pos.groups()
 props=''
 for name,value in [('Manufacturer','Wurth Elektronik'),('MPN','61300411021')]:
  props+=f'\t\t(property "{name}" "{value}"\n\t\t\t(at {x} {y} 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n'
 i=block.index('\t\t(pin "1"');block=block[:i]+props+block[i:];text=text[:a]+block+text[z:]
sch.write_text(text)
print('Updated hidden procurement fields and kept off-board pin outlines on fabrication layer only.')
