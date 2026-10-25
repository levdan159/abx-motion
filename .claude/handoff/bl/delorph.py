import re,sys
sys.path.insert(0,'/tmp/claude-1000/-home-mark-Documents-VE-V3/ca86dfbf-052d-499b-8b8f-07944423ef8f/scratchpad/bl')
import sx
def near(a,b): return abs(a[0]-b[0])<0.01 and abs(a[1]-b[1])<0.01
def run(f,refs):
    t=open(f).read(); kill=[]
    spans=sx.spans(t)
    wires=[(a,e,[tuple(map(float,p)) for p in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)',t[a:e])]) for a,e,h in spans if h=='wire']
    syms=[(a,e,t[a:e]) for a,e,h in spans if h=='symbol']
    for a,e,h in spans:
        pass
    for s in sx.symbols(t):
        if s[2] not in refs: continue
        b=t[s[0]:s[1]]; x,y,r=map(float,re.search(r'\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)',b).groups())
        kill.append((s[0],s[1]))
        pts=[(x,y-3.81),(x,y+3.81)] if r in(0,180) else [(x-3.81,y),(x+3.81,y)]
        for p in pts:
            for wa,we,c in wires:
                if any(near(q,p) for q in c):
                    far=[q for q in c if not near(q,p)][0]
                    kill.append((wa,we))
                    others=[w for w in wires if w[0]!=wa and any(near(q,far) for q in w[2])]
                    if others: print(f,'far end shared with other wire',far); continue
                    for sa,se,sb in syms:
                        if sa==s[0]: continue
                        m=re.search(r'\(at ([-\d.]+) ([-\d.]+) ',sb)
                        if m and near((float(m.group(1)),float(m.group(2))),far) and sx.prop(sb,'Reference').startswith('#'):
                            kill.append((sa,se)); print(f,'remove power sym',sx.prop(sb,'Reference'),sx.prop(sb,'Value'))
    out=[];last=0
    for a,e in sorted(set(kill)):
        out.append(t[last:a]); last=e
        while last<len(t) and t[last] in ' \t': last+=1
        if t[last:last+1]=='\n': last+=1
    out.append(t[last:]); open(f,'w').write(''.join(out)); print(f,'removed items',len(set(kill)))
run('MCU.kicad_sch',['R204','R205','R207','R208','R209','R210'])
run('Industrial_IO.kicad_sch',['R621','R622'])
