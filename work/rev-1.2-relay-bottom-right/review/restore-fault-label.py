import pcbnew as p
from pathlib import Path
r=Path.cwd();o=r/'work/rev-1.2-relay-bottom-right/review';b=p.LoadBoard(str(r/'abx-motion.kicad_pcb'));old=p.LoadBoard(str(o/'before.kicad_pcb'));original={x.m_Uuid.AsString():x for x in old.GetDrawings()}
for t in b.GetDrawings():
 if isinstance(t,p.PCB_TEXT) and t.GetText()=='M2 FLT':
  src=original[t.m_Uuid.AsString()];t.SetPosition(src.GetPosition());print('Restored M2 FLT label',p.ToMM(src.GetPosition().x),p.ToMM(src.GetPosition().y))
p.SaveBoard(str(r/'abx-motion.kicad_pcb'),b)
f=o/'place_root.py';s=f.read_text();s=s.replace(" elif isinstance(t,p.PCB_TEXT) and t.GetText()=='M2 FLT':t.SetPosition(p.VECTOR2I(p.FromMM(179.7),p.FromMM(139.25)))\n",'');f.write_text(s)
