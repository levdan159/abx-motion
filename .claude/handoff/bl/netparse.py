import re,sys
def parse(path):
    t=re.sub(r'\s+',' ',open(path).read())
    comps={}
    for m in re.finditer(r'\(comp \(ref "([^"]+)"\) \(value "([^"]*)"\) \(footprint "([^"]*)"\)(.*?)\(sheetpath \(names "([^"]+)"\)',t):
        comps[m.group(1)]=dict(value=m.group(2),fp=m.group(3),sheet=m.group(5),pins={})
    nets=t[t.index('(nets'):]
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)(?=\(net \(code|$)',nets):
        for r,p in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)',m.group(2)):
            if r in comps: comps[r]['pins'][p]=m.group(1)
    return comps
if __name__=='__main__':
    c=parse(sys.argv[1]); pre=sys.argv[2]
    for r in sorted((r for r in c if c[r]['sheet'].startswith(pre)),key=lambda r:(re.sub(r'\d','',r),int(re.sub(r'\D','',r) or 0))):
        d=c[r]; print('%s|%s|%s|%s'%(r,d['value'],d['fp'].split(':')[-1][:28],' '.join('%s=%s'%(k,v.replace(pre,'')) for k,v in sorted(d['pins'].items(),key=lambda x:(len(x[0]),x[0])))))
