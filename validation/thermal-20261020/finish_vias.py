from pathlib import Path
import pcbnew as p,json,ast
R=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent;b=p.LoadBoard(str(R/'abx-motion.kicad_pcb'));mm=p.FromMM;pt=lambda x,y:p.VECTOR2I(mm(x),mm(y));added=[];skipped=[]
s=ast.parse((O/'apply_thermal.py').read_text());ns=globals()
for n in s.body:
 if isinstance(n,ast.FunctionDef) and n.name in ['safe','via']:exec(compile(ast.Module(body=[n],type_ignores=[]),'helpers','exec'),ns)
changes=json.loads((O/'changes.json').read_text())
for ref in ['Q1','Q302','Q304','Q402','Q404','Q301','Q303','Q401','Q403']:
 f=b.FindFootprintByReference(ref);x=p.ToMM(f.GetPosition().x);y=p.ToMM(f.GetPosition().y);net=next(q.GetNetname() for q in f.Pads() if q.GetNumber()=='5');start=len(added)
 candidates=[(x+dx,y+dy) for dx in [3.9,4.6] for dy in [-2.5,-1.2,0,1.2,2.5]]+[(x+dx,y+dy) for dy in [-2.9,2.9] for dx in [-.3,1.0,2.3,3.6]]
 for xx,yy in candidates:
  if len(added)-start>=4:break
  via(ref,net,round(xx,3),round(yy,3))
 print(ref,'additional vias',len(added)-start)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(R/'abx-motion.kicad_pcb'),b)
changes['added_vias']+=added;(O/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
