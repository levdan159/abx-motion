import re,sys
sys.path.insert(0,'/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/bl')
import sx
f='abx-motion-brushless.kicad_pcb'; t=open(f).read(); out=[];last=0;c={}
for s,e,h in sx.spans(t):
    b=t[s:e]
    kill = h in('gr_text','gr_text_box','segment','via','arc','zone','group') or (h=='gr_line' and 'Silkscreen' in b) or (h in('gr_rect','gr_circle','gr_arc','gr_poly') and 'Silkscreen' in b)
    if kill: out.append(t[last:s]); last=e; c[h]=c.get(h,0)+1
out.append(t[last:]); open(f,'w').write(''.join(out)); print(c)
