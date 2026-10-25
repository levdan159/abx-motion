import re,sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import sx
SYM='/usr/share/kicad/symbols/'
def fix(path):
    t=open(path).read()
    ls,le,_=[x for x in sx.spans(t) if x[2]=='lib_symbols'][0]
    inner=t[ls:le]; out=[];n=0
    for s,e,h in sx.spans(inner,depth=1):
        blk=inner[s:e]
        m=re.match(r'\(symbol "([^":]+):([^"]+)"',blk)
        if not m: continue
        lib,name=m.groups(); f=SYM+lib+'.kicad_sym'
        if not os.path.exists(f): continue
        L=open(f).read(); cand=None
        for a,b,hh in sx.spans(L):
            if L[a:b].startswith('(symbol "%s"'%name): cand=L[a:b]; break
        if not cand or '(extends' in cand: continue
        new=cand.replace('(symbol "%s"'%name,'(symbol "%s:%s"'%(lib,name),1)
        # unit sub-symbols keep their plain names (KiCad convention inside lib_symbols)
        out.append((ls+s,ls+e,new)); n+=1
    for s,e,new in sorted(out,reverse=True): t=t[:s]+new+t[e:]
    open(path,'w').write(t); print(path,'replaced',n)
for p in sys.argv[1:]: fix(p)
