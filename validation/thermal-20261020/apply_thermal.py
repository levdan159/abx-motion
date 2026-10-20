"""One-shot local thermal copper/via additions; preserve all existing routing."""
from pathlib import Path
import pcbnew as p,shutil,json,hashlib
R=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent
B=O/'before';assert not B.exists();B.mkdir()
for f in [R/'abx-motion.kicad_pcb',*R.glob('*.kicad_sch'),R/'generate_schematics.py',R/'README.md',R/'abx-footprints.pretty/ABX_Text_Gold.kicad_mod']:
 d=B/f.relative_to(R);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));mm=p.FromMM
pt=lambda x,y:p.VECTOR2I(mm(x),mm(y));added=[];zones=[];skipped=[]
# Pre-screen against existing physical copper and drills on all copper layers.
def safe(net,x,y):
 c=p.SHAPE_CIRCLE(pt(x,y),mm(.625)) # 0.325mm annulus radius +0.30mm margin
 for f in b.GetFootprints():
  for q in f.Pads():
   if q.GetNetname()!=net and p.SHAPE.Collide(c,q.GetEffectiveShape(p.F_Cu),0):return False
   # New vias stay out of ALL exposed component lands, including same-net lands.
   if p.SHAPE.Collide(p.SHAPE_CIRCLE(pt(x,y),mm(.475)),q.GetEffectiveShape(p.F_Cu),0):return False
 for t in b.GetTracks():
  if t.GetNetname()!=net and p.SHAPE.Collide(c,t.GetEffectiveShape(t.GetLayer()),0):return False
  if isinstance(t,p.PCB_VIA) and (t.GetPosition()-pt(x,y)).EuclideanNorm()<mm(.9):return False
 return any(z.GetNetname()==net and z.IsOnLayer(p.F_Cu) and z.HitTestFilledArea(p.F_Cu,pt(x,y)) for z in b.Zones())
def via(ref,net,x,y):
 if not safe(net,x,y):skipped.append([ref,x,y]);return
 v=p.PCB_VIA(b);v.SetPosition(pt(x,y));v.SetWidth(mm(.65));v.SetDrill(mm(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);b.Add(v)
 added.append(dict(ref=ref,net=net,x=x,y=y,uuid=v.m_Uuid.AsString()))
def zone(ref,net,layer,box):
 z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet(net));z.SetAssignedPriority(4);z.SetLocalClearance(mm(.25));z.SetMinThickness(mm(.2));z.SetPadConnection(p.ZONE_CONNECTION_FULL)
 x1,y1,x2,y2=box;z.Outline().NewOutline()
 for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:z.Outline().Append(mm(x),mm(y))
 b.Add(z);zones.append(dict(ref=ref,net=net,layer=b.GetLayerName(layer),bounds_mm=box,uuid=z.m_Uuid.AsString()))
# Low-side drains have no shared power plane: bounded backside islands provide useful receiving copper.
for ref in ['Q302','Q304','Q402','Q404']:
 f=b.FindFootprintByReference(ref);x=p.ToMM(f.GetPosition().x);y=p.ToMM(f.GetPosition().y);net=next(q.GetNetname() for q in f.Pads() if q.GetNumber()=='5')
 zone(ref,net,p.B_Cu,[x-.5,y-3,x+5.0,y+3])
 for yy in [y-1.5,y,y+1.5]:via(ref,net,x+4.1,yy)
# Existing Q1 drain polygon already spans both outer faces.
for x,y in [(169.1,61.8),(169.1,63.2),(169.1,64.6),(165.0,60.2),(168.6,60.2)]:via('Q1','/Power_Supply/V_FUSED',x,y)
# Improve high-side power-plane coupling outside solder lands.
for ref in ['Q301','Q303','Q401','Q403']:
 f=b.FindFootprintByReference(ref);x=p.ToMM(f.GetPosition().x);y=p.ToMM(f.GetPosition().y)
 for yy in [y-1.5,y,y+1.5]:via(ref,'+BATT',x+4.1,yy)
# A local grounded top spreader couples the module's existing 12 EPAD holes to its surroundings.
# Entirely inside shielded body, well below antenna/feed region; no added solder apertures.
zone('U3','GND',p.F_Cu,[95.3,58.5,104.0,66.2])
# U2 has no exposed pad: grounded copper can spread heat through its ground lead.
zone('U2','GND',p.F_Cu,[132.8,77.7,137.2,79.3])
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b)
# Distinguish the actual changed copper artwork from the previous prototype revision.
for f in [R/'abx-motion.kicad_pcb',*R.glob('*.kicad_sch'),R/'generate_schematics.py',R/'abx-footprints.pretty/ABX_Text_Gold.kicad_mod']:
 s=f.read_text().replace('Rev 1.1c','Rev 1.1d').replace('(rev "1.1c")','(rev "1.1d")').replace('HARDWARE_REVISION = "1.1c"','HARDWARE_REVISION = "1.1d"');f.write_text(s)
(O/'changes.json').write_text(json.dumps(dict(revision='1.1d',added_vias=added,added_zones=zones,skipped_candidates=skipped,physical_tests='NOT RUN'),indent=2)+'\n')
print('Added vias',len(added),'zones',len(zones),'skipped',len(skipped));print(added)
