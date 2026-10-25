import re,sys
sys.path.insert(0,'/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/bl'); import sx
def items(t):
    out=[]
    for s,e,h in sx.spans(t,1):
        b=t[s:e]
        if h=='wire':
            p=re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)',b); out.append(('wire',[(float(a),float(c)) for a,c in p],s,e))
        elif h in('label','global_label','hierarchical_label','junction','no_connect'):
            m=re.search(r'\(at ([-\d.]+) ([-\d.]+)',b); n=re.search(r'"([^"]+)"',b)
            out.append((h,(float(m.group(1)),float(m.group(2))),n.group(1) if n else '',s,e))
        elif h=='symbol':
            m=re.search(r'\(at ([-\d.]+) ([-\d.]+) (\d+)\)',b); out.append(('symbol',(float(m.group(1)),float(m.group(2)),int(m.group(3))),sx.prop(b,'Reference'),re.search(r'\(lib_id "([^"]+)"',b).group(1),s,e))
    return out
def libpins(t,lib):
    ls=[x for x in sx.spans(t,1) if x[2]=='lib_symbols'][0]; inner=t[ls[0]:ls[1]]
    for s,e,h in sx.spans(inner,1):
        if inner[s:e].startswith(f'(symbol "{lib}"'):
            b=inner[s:e]; out={}
            for m in re.finditer(r'\(pin (\w+) (\w+)\s+\(at ([-\d.]+) ([-\d.]+) (\d+)\)',b):
                k=b.index('(number "',m.start()); n=re.match(r'\(number "([^"]*)"',b[k:]).group(1)
                kn=b.index('(name "',m.start()); nm=re.match(r'\(name "([^"]*)"',b[kn:]).group(1)
                out[n]=(nm,float(m.group(3)),float(m.group(4)),int(m.group(5)))
            return out
def pinpos(sym,pin):  # sym=(x,y,rot) ; KiCad: y down, lib y up; rotation ccw
    import math
    x,y,r=sym; px,py=pin[1],pin[2]; a=math.radians(r)
    rx=px*math.cos(a)-py*math.sin(a); ry=px*math.sin(a)+py*math.cos(a)
    return (round(x+rx,2),round(y-ry,2))
if __name__=='__main__':
    fn,ref=sys.argv[1],sys.argv[2]; t=open(fn).read(); it=items(t)
    sym=[i for i in it if i[0]=='symbol' and i[2]==ref][0]; lp=libpins(t,sym[3])
    for n,p in lp.items():
        pp=pinpos(sym[1],p); print(ref,'pin',n,p[0],pp)
        for i in it:
            if i[0]=='wire' and any(abs(a-pp[0])<0.01 and abs(b-pp[1])<0.01 for a,b in i[1]): print('   wire',i[1])
            if i[0] in('label','global_label','junction','hierarchical_label') and abs(i[1][0]-pp[0])<0.01 and abs(i[1][1]-pp[1])<0.01: print('   ',i[0],i[2])
