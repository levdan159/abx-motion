from pathlib import Path
import pcbnew as p,sexpdata as sx,json,re
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
name='EXT_Header_1x04_P2.54mm_RightAngle';lib=R/'abx-footprints.pretty';source=Path('/usr/share/kicad/footprints/Connector_PinHeader_2.54mm.pretty/PinHeader_1x04_P2.54mm_Horizontal.kicad_mod')
tree=sx.loads(source.read_text());tree[1]=name
S=lambda x:sx.Symbol(x)
def tag(x):return str(x[0]) if isinstance(x,list) and x else ''
def shift(x):
 if not isinstance(x,list):return
 if tag(x) in ('at','start','end','center','mid','xy') and len(x)>=3 and isinstance(x[1],(int,float)):
  x[2]=round(x[2]-7.62,6)
 else:
  for child in x:shift(child)
# Remove original pin-1 L marker; re-create it at the new pin-1 end.
for x in list(tree):
 if tag(x)=='fp_line':
  start=next((z for z in x if tag(z)=='start'),None);end=next((z for z in x if tag(z)=='end'),None)
  if start and end and (start[1:]==[-1.27,-1.27] or (start[1:]==[-1.27,0] and end[1:]==[-1.27,-1.27])):tree.remove(x)
for x in tree:
 if tag(x)=='model':
  offset=next(z for z in x if tag(z)=='offset');offset[1]=[S('xyz'),0,7.62,0]
 elif isinstance(x,list):shift(x)
 if tag(x)=='pad':
  x[1]=str(5-int(x[1]));x[3]=S('rect' if x[1]=='1' else 'circle')
  next(z for z in x if tag(z)=='drill')[1]=1.1
 if tag(x)=='descr':x[1]='Unshrouded 4-pin right-angle header, 2.54mm pitch; pin 1 at origin, row along -Y; outward bottom-edge use at 270deg. 1.1mm drills. WR-PHD 61300411021 reference.'
for a,z in [((-1.27,0),(-1.27,1.27)),((-1.27,1.27),(0,1.27))]:
 tree.append([S('fp_line'),[S('start'),*a],[S('end'),*z],[S('stroke'),[S('width'),.12],[S('type'),S('solid')]],[S('layer'),'F.SilkS']])
(lib/(name+'.kicad_mod')).write_text(sx.dumps(tree)+'\n')
b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()};changes=[];oldfps=[]
for ref in ['J502','J504']:
 old=fps[ref];oldfps.append(old);nets={q.GetNumber():q.GetNet() for q in old.Pads()};oldpad={q.GetNumber():[p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y),q.GetNetname()] for q in old.Pads()};pos=old.GetPosition()
 new=p.FootprintLoad(str(lib),name);new.SetParent(b);new.SetReference(ref);new.SetValue(old.GetValue());new.SetPath(old.GetPath());new.SetFPID(p.LIB_ID('abx-footprints',name));new.SetUuid(old.m_Uuid);new.SetOrientationDegrees(270);new.SetPosition(pos)
 for q in new.Pads():q.SetNet(nets[q.GetNumber()])
 new.Reference().SetLayer(p.F_Fab);new.Reference().SetVisible(False);new.Value().SetVisible(False)
 # Native field identifies the selected physical form; release procurement is separate.
 new.SetField('Manufacturer','Wurth Elektronik');new.SetField('MPN','61300411021')
 b.Remove(old);b.Add(new);fps[ref]=new
 changes.append({'ref':ref,'old_pads':oldpad,'new_pads':{q.GetNumber():[p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y),q.GetNetname()] for q in new.Pads()}})
# Reproject existing front and mirrored rear legends to each new pad center.
labelmap={'EN':'EN','PU':'STEP','DR':'DIR','G':'GND'}
for t in b.GetDrawings():
 if not isinstance(t,p.PCB_TEXT):continue
 x,y=p.ToMM(t.GetPosition().x),p.ToMM(t.GetPosition().y)
 for ref in ['J502','J504']:
  fp=fps[ref];ox=p.ToMM(fp.GetPosition().x)
  if abs(x-(ox+3.75))<.1 and t.GetText()==f'{ref} EXT{1 if ref=="J502" else 2}':
   t.SetPosition(p.VECTOR2I(p.FromMM(ox+3.81),p.FromMM(143.3)));continue
  if not (ox-.1<=x<=ox+7.6 and 144<y<146 and t.GetText() in labelmap):continue
  num=str(round((x-ox)/2.5)+1);q=next(q for q in fp.Pads() if q.GetNumber()==num)
  t.SetText(labelmap[t.GetText()]);t.SetPosition(p.VECTOR2I(q.GetPosition().x,p.FromMM(145.5)));t.SetTextSize(p.VECTOR2I(p.FromMM(.65),p.FromMM(.65)));t.SetTextThickness(p.FromMM(.12));t.SetMirrored(t.GetLayer()==p.B_SilkS)
# Change only the matching schematic symbol blocks, preserving all wiring/pin UUIDs.
sch=R/'Steppers_Relays.kicad_sch';text=sch.read_text();starts=[m.start() for m in re.finditer(r'^\t\(symbol\n',text,re.M)];starts.append(len(text));edits=[]
for a,z in zip(starts,starts[1:]):
 block=text[a:z]
 if not any(f'(property "Reference" "{ref}"' in block for ref in ['J502','J504']):continue
 block=block.replace('Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical','abx-footprints:'+name)
 block=block.replace('(property "Datasheet" "~"','(property "Datasheet" "https://www.we-online.com/components/products/datasheet/61300411021.pdf"')
 edits.append((a,z,block))
assert len(edits)==2
for a,z,block in reversed(edits):text=text[:a]+block+text[z:]
sch.write_text(text)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b)
(O/'changes.json').write_text(json.dumps(changes,indent=2));print('Changed J502/J504 only; preserved pad-number nets and connector row origins.')
