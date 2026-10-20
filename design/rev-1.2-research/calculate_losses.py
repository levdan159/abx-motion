"""First-order comparison, not a junction-temperature or motor qualification."""
from pathlib import Path
import csv,json
O=Path(__file__).resolve().parent
# Datasheet electrical-characteristic tables, at VM24V. Individual FET values.
parts={'DRV8461_PWP':{'typ25':(.153,.150),'max25':(.180,.185),'max125':(.285,.300)},'DRV8452_PWP':{'typ25':(.057,.060),'max25':(.068,.072),'max125':(.100,.105)}}
rows=[]
for name,conditions in parts.items():
 for current in [1,1.5,2]:
  for cond,(h,l) in conditions.items():
   watts=2*current**2*(h+l);rows.append(dict(driver=name,phase_RMS_A=current,condition=cond,HS_ohm=h,LS_ohm=l,conduction_W_per_axis=round(watts,4),conduction_W_three_axes=round(3*watts,4)))
with (O/'conduction-loss-comparison.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
assert next(x['conduction_W_per_axis'] for x in rows if x['driver']=='DRV8452_PWP' and x['condition']=='typ25' and x['phase_RMS_A']==2)==.936
assert next(x['conduction_W_per_axis'] for x in rows if x['driver']=='DRV8461_PWP' and x['condition']=='typ25' and x['phase_RMS_A']==2)==2.424
(O/'calculation-scope.json').write_text(json.dumps(dict(model='Pcond=2*Iphase_RMS^2*(R_HS+R_LS)',sources=['https://www.ti.com/lit/ds/symlink/drv8461.pdf','https://www.ti.com/lit/ds/symlink/drv8452.pdf'],scope='Sinusoidal two-phase motor excitation; table values specified at24V, not a32V guaranteed bound. Excludes switching, quiescent losses, recirculation details, board losses, self-heating and thermal coupling. Hot-resistance rows are sensitivity cases, not predicted temperatures.',physical_tests='NOT RUN'),indent=2)+'\n')
print('Calculated18 loss cases; two independent arithmetic assertions pass.')
