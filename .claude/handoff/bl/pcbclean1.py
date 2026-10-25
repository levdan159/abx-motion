import re,sys
sys.path.insert(0,'/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/bl')
import sx
SP='/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/'
sch=set(re.findall(r'\(comp\s+\(ref "([^"]*)"\)',open(SP+'n3.net').read()))
f='abx-motion-brushless.kicad_pcb'; t=open(f).read(); out=[];last=0;n=0
for s,e,h in sx.spans(t):
    if h=='footprint':
        ref=sx.prop(t[s:e],'Reference')
        if ref not in sch:
            out.append(t[last:s]); last=e; n+=1
out.append(t[last:]); open(f,'w').write(''.join(out)); print('removed',n)
