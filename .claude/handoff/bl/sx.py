"""tiny KiCad s-expression reader/writer: top-level children of a kicad_sch as (start,end) text spans."""
import re
def spans(t, depth=1):
    """yield (start,end,head) for each child list at nesting `depth` (root list = depth 0)."""
    d=0;i=0;n=len(t);out=[]
    while i<n:
        c=t[i]
        if c=='"':
            i+=1
            while t[i]!='"':
                i+=2 if t[i]=='\\' else 1
        elif c=='(':
            d+=1
            if d==depth+1: s=i
        elif c==')':
            if d==depth+1:
                m=re.match(r'\(\s*([^\s()"]+)',t[s:s+60]); out.append((s,i+1,m.group(1) if m else ''))
            d-=1
        i+=1
    return out
def prop(block,name):
    m=re.search(r'\(property "%s" "((?:[^"\\]|\\.)*)"'%re.escape(name),block); return m.group(1) if m else None
def symbols(t):
    res=[]
    for s,e,h in spans(t):
        if h=='symbol':
            b=t[s:e]
            res.append((s,e,prop(b,'Reference'),prop(b,'Value'),prop(b,'Footprint'),re.search(r'\(lib_id "([^"]+)"',b).group(1) if '(lib_id' in b else None))
    return res
