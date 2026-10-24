from pathlib import Path
import pcbnew,json,math
from shapely.geometry import box
R=Path.cwd();O=R/'work/drc-cleanup-20261024';b=pcbnew.LoadBoard(str(R/'abx-motion.kicad_pcb'));uid=lambda t:t.m_Uuid.AsString();fs={f.GetReference():f for f in b.GetFootprints()};report=json.loads((O/'before-drc.json').read_text());changes=[];holds=[]
# A GND-assigned pad defines both copper and mask, replacing an unassigned
# mask graphic. Exact original4x4 aperture; no paste; original thermal vias kept.
for g in list(b.GetDrawings()):
 if uid(g)=='bc9cc23d-9aff-4ac7-b282-03f9d1109290':holds.append(g);b.Remove(g)
f=pcbnew.FOOTPRINT(b);f.SetReference('TIM_ESP');f.SetValue('GND TIM 4x4 NO PASTE');f.SetFPID(pcbnew.LIB_ID('abx-footprints','TIM_GND_4x4_Bottom'));f.SetAttributes(pcbnew.FP_BOARD_ONLY|pcbnew.FP_EXCLUDE_FROM_BOM|pcbnew.FP_EXCLUDE_FROM_POS_FILES);f.SetLayer(pcbnew.B_Cu);f.SetPosition(pcbnew.VECTOR2I(99500000,62460000));f.Reference().SetVisible(False);f.Value().SetVisible(False)
p=pcbnew.PAD(f);p.SetNumber('1');p.SetShape(pcbnew.PAD_SHAPE_RECT);p.SetAttribute(pcbnew.PAD_ATTRIB_SMD);p.SetSize(pcbnew.VECTOR2I(4000000,4000000));p.SetPosition(f.GetPosition());layers=pcbnew.LSET();layers.AddLayer(pcbnew.B_Cu);layers.AddLayer(pcbnew.B_Mask);p.SetLayerSet(layers);p.SetNetCode(b.FindNet('GND').GetNetCode());p.SetLocalSolderMaskMargin(0);f.Add(p);b.Add(f)
changes.append(dict(action='ESP TIM mask replaced with net-aware GND pad',size_mm=[4,4],center_mm=[99.5,62.46],paste=False))
# Narrow only the legend frame's left edge clear of the RJ45 drill/pad field.
for g in b.GetDrawings():
 if g.GetClass()=='PCB_SHAPE' and g.GetLayer()==pcbnew.B_SilkS:
  for method in ['Start','End']:
   pos=getattr(g,'Get'+method)()
   if pos.x==124000000 and pos.y in [58000000,63200000,94200000]:getattr(g,'Set'+method)(pcbnew.VECTOR2I(130500000,pos.y))
 if g.GetClass()=='PCB_TEXT' and g.GetText()=='ABX-MOTION Rev 1.2a':g.SetText('ABX-MOTION Rev 1.2b')
# Crystal lower silk line infringes the adjacent IC pin-one mark. Keep its fab
# outline and the other silk edges, instead of moving any physical component.
y=fs['Y801']
for g in y.GraphicalItems():
 if uid(g)=='66b0b58b-385a-4a33-9b7f-f55dbe736b96':g.SetLayer(pcbnew.F_Fab);changes.append(dict(action='Crystal silk edge moved to Fab for pin-marker clearance'))
texts={}
for g in b.GetDrawings():
 if g.GetClass()=='PCB_TEXT':texts[uid(g)]=g
for ff in b.GetFootprints():
 for t in [ff.Reference(),ff.Value()]+[g for g in ff.GraphicalItems() if g.GetClass()=='PCB_TEXT']:texts[uid(t)]=t
move=set()
for v in report['violations']:
 if v['type'] in ['silk_overlap','silk_over_copper']:
  for i in v['items']:
   if i['description'].startswith('Reference field of'):move.add(i['uuid'])
move.add('fee92d4e-0044-4fa5-a93c-2d9e4a9e4750')
def bbox(o):
 bb=o.GetBoundingBox();return box(bb.GetLeft()/1e6,bb.GetTop()/1e6,bb.GetRight()/1e6,bb.GetBottom()/1e6)
def obstacles(t):
 layer=t.GetLayer();mask=pcbnew.F_Mask if layer==pcbnew.F_SilkS else pcbnew.B_Mask;obs=[]
 for ff in b.GetFootprints():
  for pad in ff.Pads():
   if pad.IsOnLayer(mask):obs.append(bbox(pad).buffer(.18))
  for g in ff.GraphicalItems():
   if g.GetClass()=='PCB_SHAPE' and g.GetLayer()==layer:obs.append(bbox(g).buffer(.15))
 for g in b.GetDrawings():
  if g.GetClass()=='PCB_SHAPE' and g.GetLayer()==layer:obs.append(bbox(g).buffer(.15))
 for u,q in texts.items():
  if u!=uid(t) and u not in move and q.IsVisible() and q.GetLayer()==layer:obs.append(bbox(q).buffer(.18))
 return obs
for u in sorted(move):
 t=texts[u];old=t.GetPosition();ox,oy=old.x/1e6,old.y/1e6;name=t.GetText();obs=obstacles(t);oldsize=t.GetTextSize();size=min(oldsize.x/1e6,.8);t.SetTextSize(pcbnew.VECTOR2I(round(size*1e6),round(size*1e6)));t.SetTextThickness(min(t.GetTextThickness(),120000))
 candidates=[]
 if name in ['J711','J712','J713']:candidates.append((ox,151.8))
 for dx in range(-32,33):
  for dy in range(-32,33):candidates.append((ox+dx*.25,oy+dy*.25))
 candidates.sort(key=lambda p:math.dist((ox,oy),p))
 if name in ['J711','J712','J713']:candidates=[(ox,151.8)]+candidates
 found=False
 for x,y in candidates:
  t.SetPosition(pcbnew.VECTOR2I(round(x*1e6),round(y*1e6)));bb=bbox(t)
  if not box(45.6,48.6,201.4,152.4).contains(bb):continue
  if any(bb.intersects(q) for q in obs):continue
  changes.append(dict(text=name,old=[ox,oy],new=[x,y]));found=True;break
 if not found:t.SetPosition(old);print('No text site found',name)
 move.remove(u)
b.BuildConnectivity();pcbnew.ZONE_FILLER(b).Fill(b.Zones());pcbnew.SaveBoard(str(R/'abx-motion.kicad_pcb'),b);(O/'thermal-silk-changes.json').write_text(json.dumps(changes,indent=2)+'\n');print('Thermal/silk edits',len(changes))
