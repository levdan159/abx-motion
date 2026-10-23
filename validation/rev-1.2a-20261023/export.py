"""Export current KiCad sources without legacy generators or board mutation."""
from pathlib import Path
import subprocess
O=Path(__file__).resolve().parent;R=O.parents[1];P=R/'production/rev-1.2a-20261023';B=str(R/'abx-motion.kicad_pcb');G=str(P/'gerbers')+'/'
commands=[['pcb','export','gerbers','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts','--subtract-soldermask','--check-zones','--output',G,B],['pcb','export','drill','--format','excellon','--drill-origin','absolute','--excellon-separate-th','--excellon-units','mm','--generate-report','--report-path',str(P/'drill-report.txt'),'--output',G,B]]
for side,layers in [('top','F.Fab,F.Silkscreen,Edge.Cuts'),('bottom','B.Fab,B.Silkscreen,Edge.Cuts')]:
 commands.append(['pcb','export','svg','--layers',layers,'--sketch-pads-on-fab-layers','--fit-page-to-board','--exclude-drawing-sheet','--mode-single',*(['--mirror'] if side=='bottom' else []),'--output',str(P/f'assembly/{side}-assembly.svg'),B])
 commands.append(['pcb','render','--width','1800','--height','1200','--side',side,'--background','opaque','--quality','basic','--output',str(P/f'assembly/{side}.png'),B])
with open(O/'export.log','w') as log:
 for cmd in commands:subprocess.run(['kicad-cli',*cmd],check=True,stdout=log,stderr=log)
print('Exported Gerbers, separate PTH/NPTH drills, front/rear assembly drawings and renders.')
