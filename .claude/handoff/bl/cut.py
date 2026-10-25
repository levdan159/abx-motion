import re,sys,uuid
sys.path.insert(0,sys.path[0]); import sx
ROOT='abx-motion-brushless.kicad_sch'
DROP_SHEETS={'DC_Motor_1','DC_Motor_2','Steppers_and_Relays'}
DROP_NETS={'M1_CS','M1_nFAULT','M2_CS','M2_nFAULT','M1_PWM_PH','M1_PWM_EN','M2_PWM_PH','M2_PWM_EN',
           'STEP1_PUL','STEP1_DIR','STEP2_PUL','STEP2_DIR','STEP1_EN','STEP2_EN','RELAY_1','RELAY_2'}
def cut(t,spans_to_cut):
    for s,e in sorted(spans_to_cut,reverse=True):
        # swallow the leading whitespace/newline of the block
        j=s
        while j>0 and t[j-1] in ' \t': j-=1
        if j>0 and t[j-1]=='\n': j-=1
        t=t[:j]+t[e:]
    return t
# ---- root
t=open(ROOT).read()
rm=[];keep_pins=[]
for s,e,h in sx.spans(t):
    b=t[s:e]
    if h in('wire','label'): rm.append((s,e))
    elif h=='sheet':
        if sx.prop(b,'Sheetname') in DROP_SHEETS: rm.append((s,e))
t=cut(t,rm)
# drop pins of removed nets from the remaining sheets
rm=[]
for s,e,h in sx.spans(t):
    if h=='sheet':
        for ps,pe,ph in sx.spans(t[s:e],depth=1):
            pass
# pins are depth-2 children of the sheet list: scan manually
rm=[]
for s,e,h in sx.spans(t):
    if h!='sheet': continue
    blk=t[s:e]
    for ps,pe,ph in sx.spans(blk,depth=1):
        if ph=='pin' and re.match(r'\(pin "([^"]+)"',blk[ps:pe]).group(1) in DROP_NETS: rm.append((s+ps,s+pe))
t=cut(t,rm)
# regenerate stubs+labels for each remaining pin
add=[]
for s,e,h in sx.spans(t):
    if h!='sheet': continue
    for name,x,y,a in re.findall(r'\(pin "([^"]+)" \w+\s*\(at ([\d.]+) ([\d.]+) (\d+)\)',t[s:e]):
        x=float(x);y=float(y);a=int(a); x2=x+7.62 if a==0 else x-7.62
        j='left' if a==0 else 'right'
        add.append(f'\t(wire (pts (xy {x:g} {y:g}) (xy {x2:g} {y:g})) (stroke (width 0) (type default)) (uuid "{uuid.uuid4()}"))\n'
                   f'\t(label "{name}" (at {x2:g} {y:g} {a}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {j} bottom)) (uuid "{uuid.uuid4()}"))\n')
i=t.index('\t(sheet\n') if '\t(sheet\n' in t else t.index('(sheet')
t=t[:i]+''.join(add)+t[i:]
open(ROOT,'w').write(t)
# ---- sub-sheets: drop hierarchical labels of removed nets (+ wires ending on them)
for f in ('MCU.kicad_sch','Industrial_IO.kicad_sch'):
    t=open(f).read(); rm=[];pts=[]
    for s,e,h in sx.spans(t):
        if h=='hierarchical_label' and re.search(r'"([^"]+)"',t[s:e]).group(1) in DROP_NETS:
            rm.append((s,e)); pts.append(re.search(r'\(at ([\d.]+) ([\d.]+)',t[s:e]).groups())
    for s,e,h in sx.spans(t):
        if h=='wire':
            for x,y in re.findall(r'\(xy ([\d.]+) ([\d.]+)\)',t[s:e]):
                if (x,y) in pts: rm.append((s,e)); break
    print(f,'removing',len(rm),'items')
    open(f,'w').write(cut(t,rm))
