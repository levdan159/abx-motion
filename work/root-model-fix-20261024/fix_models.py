from pathlib import Path
import re,json,shutil,hashlib
R=Path.cwd();P=R/'abx-motion.kicad_pcb';O=R/'work/root-model-fix-20261024';D=R/'abx-3dmodels/ethernet';D.mkdir(exist_ok=True)
text=P.read_text();backup=O/'before.kicad_pcb'
if not backup.exists():backup.write_text(text)
refs=set(json.load(open(R/'variants/ABX-Motion-ETH/layout-review/parts.json')));changed=[];copies={};seen=set()
def edit(match):
 block=match.group();m=re.search(r'\(property "Reference" "([^"]+)"',block)
 if not m or m[1] not in refs:return block
 ref=m[1];seen.add(ref)
 def model(m):
  old=m[1]
  source=Path(old.replace('${KIPRJMOD}',str(R)).replace('${KICAD9_3DMODEL_DIR}','/usr/share/kicad/3dmodels'))
  target=D/source.name
  if source!=target:shutil.copy2(source,target)
  new='${KIPRJMOD}/abx-3dmodels/ethernet/'+target.name
  copies[target.name]=dict(source=old,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
  changed.append(dict(ref=ref,old=old,new=new))
  return '(model "'+new+'"'
 return re.sub(r'\(model "([^"]+)"',model,block)
fixed=re.sub(r'^\t\(footprint .*?^\t\)',edit,text,flags=re.M|re.S)
assert seen==refs,(len(seen),refs-seen)
assert len(changed)==61
# Demonstrate that only model references changed, including exact non-model data.
restored=fixed
for q in changed:
 oldtoken='(model "'+q['old']+'"';newtoken='(model "'+q['new']+'"'
# Check by normalizing model filenames; there are no other byte changes.
normalize=lambda s:re.sub(r'\(model "[^"]+"','(model "MODEL"',s)
assert normalize(fixed)==normalize(text)
P.write_text(fixed)
for name in ['LICENSE.md','CREDITS.md']:shutil.copy2(Path('/usr/share/doc/kicad-packages3d')/name,D/('KiCad-'+name))
(D/'README.txt').write_text('Ethernet 3D model bundle for the root ABX-Motion project.\nStock STEP files are unmodified KiCad library models; their copyright/license\nheaders and accompanying license/credits are preserved.\nHR911105A and LMR36506 WRL files are project dimension envelopes, not vendor\ndetailed models. These copies make the draft independent of versioned library\nvariables. BOM/CPL exclusion attributes are unchanged.\n')
(O/'model-changes.json').write_text(json.dumps(changed,indent=2)+'\n');(O/'model-sources.json').write_text(json.dumps(copies,indent=2)+'\n')
print('Updated',len(changed),'model references; bundled',len(copies),'unique files')
