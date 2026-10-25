import re,sys,uuid,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import sx
U=lambda:str(uuid.uuid4())
def rw(path,fn):
    t=open(path).read(); t=fn(t); open(path,'w').write(t)
def cut_span(t,s,e):
    j=s
    while t[j-1] in ' \t': j-=1
    if t[j-1]=='\n': j-=1
    return t[:j]+t[e:]
# ---------- 1. root: grow MCU sheet, add CAN pins, rebuild stubs
def root(t):
    for s,e,h in sx.spans(t):
        if h=='sheet' and sx.prop(t[s:e],'Sheetname')=='MCU_and_Encoders':
            b=t[s:e]
            b=b.replace('(size 55.88 76.2)','(size 55.88 86.36)')
            tmpl=re.search(r'\t\t\(pin "I2C_SDA".*?\n\t\t\)\n',b,re.S).group(0)
            pins=''
            for name,y in (('CAN_H',104.14),('CAN_L',109.22)):
                p=re.sub(r'"I2C_SDA"','"%s"'%name,tmpl); p=re.sub(r'bidirectional','bidirectional',p)
                p=re.sub(r'\(at ([\d.]+) ([\d.]+) (\d+)\)','(at 180.34 %s 0)'%y,p,count=1)
                p=re.sub(r'\(uuid "[^"]+"\)','(uuid "%s")'%U(),p)
                pins+=p
            i=b.index('\t\t(instances')
            b=b[:i]+pins+b[i:]
            t=t[:s]+b+t[e:]; break
    # drop old stubs
    rm=[(s,e) for s,e,h in sx.spans(t) if h in('wire','label')]
    for s,e in sorted(rm,reverse=True): t=cut_span(t,s,e)
    add=[]
    for s,e,h in sx.spans(t):
        if h!='sheet': continue
        for name,x,y,a in re.findall(r'\(pin "([^"]+)" \w+\s*\(at ([\d.]+) ([\d.]+) (\d+)\)',t[s:e]):
            x=float(x);y=float(y);a=int(a); x2=x+7.62 if a==0 else x-7.62
            j='left' if a==0 else 'right'
            add.append(f'\t(wire (pts (xy {x:g} {y:g}) (xy {x2:g} {y:g})) (stroke (width 0) (type default)) (uuid "{U()}"))\n'
                       f'\t(label "{name}" (at {x2:g} {y:g} {a}) (fields_autoplaced yes) (effects (font (size 1.27 1.27)) (justify {j} bottom)) (uuid "{U()}"))\n')
    i=t.index('(sheet\n') if '(sheet\n' in t else t.index('(sheet')
    i=t.rfind('\n',0,i)+1
    return t[:i]+''.join(add)+t[i:]
rw('abx-motion-brushless.kicad_sch',root)
# ---------- 2. MCU hier labels CAN_H / CAN_L
def mcu(t):
    add=''
    for name,x,y in (('CAN_H',129.54,215.9),('CAN_L',129.54,218.44)):
        add+=f'\t(hierarchical_label "{name}"\n\t\t(shape bidirectional)\n\t\t(at {x} {y} 0)\n\t\t(effects (font (size 1.27 1.27)) (justify left))\n\t\t(uuid "{U()}")\n\t)\n'
    i=t.index('\t(sheet_instances') if '\t(sheet_instances' in t else len(t)-2
    return t[:i]+add+t[i:]
rw('MCU.kicad_sch',mcu)
# ---------- 3. ESC instances (3xx / 4xx)
ROOT='f9149098-3f23-438d-bdc2-2e278b5ca35b'; S1='68e0475f-9c75-41f9-88c7-a3831640edb7'; S2='df9be12f-039b-4c8b-99bb-7b46ec8aece4'
def esc(t):
    out=[]
    for s,e,r,v,fp,l in sx.symbols(t):
        if not r: continue
        b=t[s:e]
        r2=re.sub(r'(\D+)3(\d\d)$',r'\g<1>4\2',r)
        unit=re.search(r'\(unit (\d+)\)',b[b.index('(instances'):]).group(1) if '(instances' in b else '1'
        inst=(f'(instances\n\t\t\t(project "abx-motion-brushless"\n\t\t\t\t(path "/{ROOT}/{S1}"\n\t\t\t\t\t(reference "{r}")\n\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n'
              f'\t\t\t\t(path "/{ROOT}/{S2}"\n\t\t\t\t\t(reference "{r2}")\n\t\t\t\t\t(unit {unit})\n\t\t\t\t)\n\t\t\t)\n\t\t)')
        if '(instances' in b:
            i=b.index('(instances'); 
            # find matching close
            d=0
            for k in range(i,len(b)):
                if b[k]=='(':d+=1
                elif b[k]==')':
                    d-=1
                    if d==0: j=k+1;break
            nb=b[:i]+inst+b[j:]
        else:
            nb=b[:-1]+'\n\t\t'+inst+'\n\t)'
        out.append((s,e,nb))
    for s,e,nb in sorted(out,reverse=True): t=t[:s]+nb+t[e:]
    return t
rw('ESC_Channel.kicad_sch',esc)
# ---------- 4. Power: VBUS global label + PWR_FLAG at J1 pin 1
def power(t):
    x,y=45.72,71.12
    lab=f'\t(global_label "VBUS"\n\t\t(shape passive)\n\t\t(at {x} {y} 0)\n\t\t(effects (font (size 1.27 1.27)) (justify left))\n\t\t(uuid "{U()}")\n\t)\n'
    flag=f'''\t(symbol
\t\t(lib_id "power:PWR_FLAG")
\t\t(at {x} {y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{U()}")
\t\t(property "Reference" "#FLG058"
\t\t\t(at {x} {y-3.81} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Value" "PWR_FLAG"
\t\t\t(at {x} {y-6.35} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Footprint" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Datasheet" "~"
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(pin "1"
\t\t\t(uuid "{U()}")
\t\t)
\t\t(instances
\t\t\t(project "abx-motion-brushless"
\t\t\t\t(path "/{ROOT}/383ff9ef-8565-4c62-b17f-0912fd19804f"
\t\t\t\t\t(reference "#FLG058")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)
'''
    i=t.index('\t(sheet_instances') if '\t(sheet_instances' in t else len(t)-2
    return t[:i]+lab+flag+t[i:]
rw('Power.kicad_sch',power)
print('done')
