"""Add reviewed LCSC fields only; no board geometry/routing serialization."""
from pathlib import Path
import json,re,uuid
O=Path(__file__).resolve().parent;ROOT=O.parents[1];sel=json.loads((O/'selections.json').read_text());changes=[]
def end(s,start):
 d=0;quoted=False;esc=False
 for i in range(start,len(s)):
  c=s[i]
  if quoted:
   if esc:esc=False
   elif c=='\\':esc=True
   elif c=='"':quoted=False
  elif c=='"':quoted=True
  elif c=='(':d+=1
  elif c==')':
   d-=1
   if not d:return i+1
 raise ValueError('unbalanced')
for path in [ROOT/'abx-motion.kicad_pcb',*ROOT.glob('*.kicad_sch')]:
 s=path.read_text();edits=[];pcb=path.suffix=='.kicad_pcb';pattern=r'\n\t\(footprint ' if pcb else r'\n\t\(symbol\n'
 for m in re.finditer(pattern,s):
  a=m.start()+2;z=end(s,a);block=s[a:z];ref=re.search(r'\(property "Reference" "([^"]+)"',block)
  if not ref or ref[1] not in sel:continue
  ref=ref[1];old=re.search(r'\(property "LCSC" "([^"]*)"',block)
  if old:
   assert old[1]==sel[ref],(path,ref,old[1],sel[ref]);continue
  vr=re.search(r'\(property "Value" ',block);assert vr
  va=vr.start();vz=end(block,va);field=block[va:vz];field=re.sub(r'^\(property "Value" "(?:\\.|[^"\\])*"',f'(property "LCSC" "{sel[ref]}"',field)
  if pcb:
   field=re.sub(r'\(uuid "[^"]+"\)',f'(uuid "{uuid.uuid4()}" )',field)
   if '(hide yes)' not in field:field=field.replace('\n\t\t\t(effects','\n\t\t\t(hide yes)\n\t\t\t(effects',1)
  else:
   if '(hide yes)' not in field:field=field.replace('\n\t\t\t(effects','\n\t\t\t(effects',1).replace('\n\t\t\t)\n\t\t)', '\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)',1)
  edits.append((a+vz,a+vz,'\n\t\t'+field));changes.append({'file':path.name,'ref':ref,'LCSC':sel[ref]})
 for a,z,t in reversed(edits):s=s[:a]+t+s[z:]
 if edits:path.write_text(s)
(O/'metadata-changes.json').write_text(json.dumps(changes,indent=2)+'\n');print('Added',len(changes),'metadata fields')
