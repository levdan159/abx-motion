"""Publish only native-refilled zone polygons; preserve original tracks/pads/nets exactly."""
from pathlib import Path
import re,json
import pcbnew as p
O=Path(__file__).resolve().parent;R=O.parents[1];src=R/'abx-motion.kicad_pcb';before=src.read_text();stage=Path('/tmp/rev1.2a-fill');stage.mkdir(exist_ok=True)
s=(O/'apply_metadata.py').read_text();exec(s[s.index('def end('):s.index('for path in')])
b=p.LoadBoard(str(src));p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(stage/'refilled.kicad_pcb'),b);new=(stage/'refilled.kicad_pcb').read_text()
def zones(s):
 out={}
 for m in re.finditer(r'\n\t\(zone\b',s):
  a=m.start()+2;z=end(s,a);v=s[a:z];uid=re.search(r'\(uuid "([^"]+)"\)',v)[1];out[uid]=(a,z,v)
 return out
oldz,newz=zones(before),zones(new);assert oldz.keys()==newz.keys();edits=[]
for uid,(a,z,old) in oldz.items():
 fresh=newz[uid][2]
 assert re.search(r'\(net [^\n]+',old)[0]==re.search(r'\(net [^\n]+',fresh)[0]
 newfills=[]
 for m in re.finditer(r'\(filled_polygon\b',fresh):newfills.append(fresh[m.start():end(fresh,m.start())])
 for m in reversed(list(re.finditer(r'\(filled_polygon\b',old))):old=old[:m.start()]+old[end(old,m.start()):]
 old=old[:-1]+'\n'+''.join('\t\t'+f+'\n' for f in newfills)+'\t)';edits.append((a,z,old))
for a,z,t in reversed(edits):before=before[:a]+t+before[z:]
src.write_text(before);print('Published refilled polygons for',len(edits),'zones; source tracks/pads untouched.')
