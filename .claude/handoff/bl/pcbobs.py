import re,sys
sys.path.insert(0,'/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/bl')
import sx
f='abx-motion-brushless.kicad_pcb'; t=open(f).read()
dead={'R204','R205','R207','R208','R209','R210','R621','R622'}
pat=re.compile(r'STEP|RELAY|MICROSTEP|Servo|Stepper|H-Bridge|FLT|MOTOR [12]|^M[12][+-]?$',re.I)
out=[];last=0;nf=nt=0;txt=[]
for s,e,h in sx.spans(t):
    b=t[s:e]
    if h=='footprint' and sx.prop(b,'Reference') in dead: out.append(t[last:s]); last=e; nf+=1
    elif h=='gr_text':
        m=re.match(r'\(gr_text "((?:[^"\\]|\\.)*)"',b)
        if m and pat.search(m.group(1)) and 'LIM' not in m.group(1): out.append(t[last:s]); last=e; nt+=1; txt.append(m.group(1)[:40])
out.append(t[last:]); open(f,'w').write(''.join(out)); print('footprints',nf,'texts',nt); print(txt)
