from pathlib import Path
import csv,json,subprocess,hashlib
O=Path(__file__).resolve().parent;R=O.parents[1];P=R/'production/rev-1.2a-20261023';old={r['Designator']:r for r in csv.DictReader(open(O/'before/cpl.csv'))};new={r['Designator']:r for r in csv.DictReader(open(P/'abx-motion-rev1.2a-jlcpcb-cpl.csv'))};assert old.keys()==new.keys();changes=[]
for ref,row in new.items():
 b=old[ref];diff={k:[b[k],row[k]] for k in row if b[k]!=row[k]}
 if diff:
  assert set(diff)=={'Rotation'},(ref,diff);assert (float(row['Rotation'])-float(b['Rotation']))%360==180;changes.append({'ref':ref,**diff})
assert {x['ref'] for x in changes}=={'J102','J301','J401','LED201','LED202','LED_FLT1','LED_FLT2'}
assert (P/'abx-motion-rev1.2a-jlcpcb-cpl.csv').read_bytes()==(P/'abx-motion-rev1.2a-jlcpcb-cpl-corrected.csv').read_bytes()
unchanged=[R/'abx-motion.kicad_pcb',*R.glob('*.kicad_sch'),P/'abx-motion-rev1.2a-jlcpcb-bom.csv',P/'abx-motion-rev1.2a-gerbers.zip',*(P/'gerbers').glob('*')]
for p in unchanged:
 original=subprocess.check_output(['git','show','3077444:'+str(p.relative_to(R))]);assert original==p.read_bytes(),p
report={'actual_exported_CPL_rows':len(new),'changed_rows':changes,'all_centers_and_other_CPL_fields_identical':True,'corrected_alias_matches_canonical':True,'PCB_schematics_BOM_Gerbers_identical_to_3077444':True,'reviewed_remaining_rotations':len(new)-len(changes),'review_notes':'Supplier functional K/A mapping and mechanical wire-entry constraints applied; K501/K502 manufacturer alignment still required.'};(O/'export-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
