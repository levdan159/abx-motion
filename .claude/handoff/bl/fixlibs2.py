import re,sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import sx
def blocks(path):
    t=open(path).read(); ls,le,_=[x for x in sx.spans(t) if x[2]=='lib_symbols'][0]
    inner=t[ls:le]; d={}
    for s,e,h in sx.spans(inner,depth=1):
        m=re.match(r'\(symbol "([^"]+)"',inner[s:e])
        if m: d[m.group(1)]=inner[s:e]
    return t,ls,le,d
donors={}
for p in ('Power.kicad_sch','MCU.kicad_sch','Industrial_IO.kicad_sch'):
    donors.update({k:v for k,v in blocks(p)[3].items()})
t,ls,le,mine=blocks(sys.argv[1]); inner=t[ls:le]; n=0;missing=[]
for s,e,h in sorted(sx.spans(inner,depth=1),reverse=True):
    m=re.match(r'\(symbol "([^"]+)"',inner[s:e])
    if m and m.group(1) in donors and not m.group(1).startswith('abx:'):
        inner=inner[:s]+donors[m.group(1)]+inner[e:]; n+=1
    elif m: missing.append(m.group(1))
t=t[:ls]+inner+t[le:]; open(sys.argv[1],'w').write(t); print('replaced',n,'not in donors:',missing)
