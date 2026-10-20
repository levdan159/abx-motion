from pathlib import Path
import subprocess,json,sys
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
for k in range(25):
 j=json.loads((O/'drc.json').read_text());assert not j['unconnected_items'];assert not any(v['severity']=='error' for v in j['violations'])
 extra=[v for v in j['violations'] if v['type']!='lib_footprint_mismatch']
 if not extra:print('Clean after',k,'additional pruning passes.',flush=True);break
 assert all(v['type'] in ['track_dangling','via_dangling'] for v in extra)
 print('Pruning remaining',len(extra),'local remnants, pass',k+1,flush=True)
 subprocess.run(['/usr/bin/python3',str(O/'cleanup.py'),'drc.json'],cwd=R,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 subprocess.run(['/usr/bin/kicad-cli','pcb','drc','--schematic-parity','--format','json','--output',str(O/'drc.json'),str(R/'abx-motion.kicad_pcb')],cwd=R,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
else:raise RuntimeError('Pruning limit reached')
