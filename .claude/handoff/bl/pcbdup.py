import re,sys
sys.path.insert(0,'/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/bl')
import sx
SP='/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/'
n=open(SP+'n3.net').read()
good=set(sp.rstrip('/')+'/'+ts for sp,ts in re.findall(r'\(sheetpath\s+\(names "[^"]*"\)\s+\(tstamps "([^"]*)"\)\s+\)\s+\(tstamps "([^"]*)"\)',n))
if not good: good=set(sp.rstrip('/')+'/'+ts for sp,ts in re.findall(r'\(sheetpath\s+\(tstamps "([^"]*)"\)\s*\)?\s*\(tstamps "([^"]*)"\)',n))
print('good paths',len(good))
t=open('abx-motion-brushless.kicad_pcb').read()
bad=[]
for s,e,h in sx.spans(t):
    if h=='footprint':
        b=t[s:e]; m=re.search(r'\(path "([^"]*)"',b)
        p=m.group(1) if m else ''
        if p=='': bad.append((s,e,sx.prop(b,'Reference'),sx.prop(b,'Value'),p[-12:]))
print('bad',len(bad))
for x in bad[:70]: print(x[2:])
if len(sys.argv)>1:
    out=[];last=0
    for s,e,*_ in bad: out.append(t[last:s]); last=e
    out.append(t[last:]); open('abx-motion-brushless.kicad_pcb','w').write(''.join(out)); print('written')
