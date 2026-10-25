import re,sys,os,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import sx
def libpins(t):
    ls=[x for x in sx.spans(t) if x[2]=='lib_symbols'][0]; inner=t[ls[0]:ls[1]]; d={}
    for s,e,h in sx.spans(inner,depth=1):
        b=inner[s:e]; name=re.match(r'\(symbol "([^"]+)"',b).group(1)
        d[name]=[(float(x),float(y)) for x,y in re.findall(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) \d+\)',b)]
    return d
def pinpos(sym,lp):
    x,y,a=re.search(r'\(at ([-\d.]+) ([-\d.]+) (\d+)',sym).groups(); x=float(x);y=float(y);a=math.radians(int(a))
    lid=re.search(r'\(lib_id "([^"]+)"',sym).group(1)
    mx='(mirror x)' in sym; my='(mirror y)' in sym
    out=[]
    for px,py in lp[lid]:
        if mx: py=-py
        if my: px=-px
        rx=px*math.cos(a)-py*math.sin(a); ry=px*math.sin(a)+py*math.cos(a)
        out.append((round(x+rx,2),round(y-ry,2)))
    return out
def move(t,ref,nx,ny):
    lp=libpins(t)
    for s,e,r,v,fp,l in sx.symbols(t):
        if r!=ref: continue
        sym=t[s:e]; ox,oy=map(float,re.search(r'\(at ([-\d.]+) ([-\d.]+)',sym).groups()); dx=round(nx-ox,4); dy=round(ny-oy,4)
        pins=set(pinpos(sym,lp))
        def shift(m): return '(at %g %g%s)'%(round(float(m.group(1))+dx,4),round(float(m.group(2))+dy,4),m.group(3) or '')
        new=re.sub(r'\(at ([-\d.]+) ([-\d.]+)( \d+)?\)',shift,sym)
        edits=[(s,e,new)]
        for a,b,h in sx.spans(t):
            if h in('label','global_label','hierarchical_label','no_connect'):
                q=tuple(round(float(z),2) for z in re.search(r'\(at ([-\d.]+) ([-\d.]+)',t[a:b]).groups())
                if q in pins: edits.append((a,b,re.sub(r'\(at ([-\d.]+) ([-\d.]+)( \d+)?\)',shift,t[a:b],count=1)))
        for a,b,n in sorted(edits,reverse=True): t=t[:a]+n+t[b:]
        return t,len(edits)-1
    raise SystemExit('no ref '+ref)
if __name__=='__main__':
    path=sys.argv[1]; t=open(path).read()
    for spec in sys.argv[2:]:
        ref,x,y=spec.split(','); t,n=move(t,ref,float(x),float(y)); print(ref,'->',x,y,'labels moved',n)
    open(path,'w').write(t)
