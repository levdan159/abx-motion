"""Replace D2 locally with the drawing-checked TI pulse clamp, without rerouting."""
from pathlib import Path
import sys,re,json
import pcbnew as p
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import generate_schematics as g
from robustness_support import tvs3300_symbol,place_tvs3300,TVS_FP,TVS_SKU

def blocks(s,name):
    depth=0;start=None
    for m in re.finditer(r'"(?:\\.|[^"\\])*"|\(|\)',s):
        if m.group()=='(':
            if depth==1:start=m.start()
            depth+=1
        elif m.group()==')':
            depth-=1
            if depth==1 and start is not None:
                block=s[start:m.end()]
                if re.match(r'\('+re.escape(name)+r'(?:\s|\))',block):yield start,m.end(),block
def node(n,key):return next(c for c in n[1:] if isinstance(c,list) and c and c[0]==('sym',key))
def at(n):return tuple(float(v[1]) for v in node(n,'at')[1:3])

# Install one local symbol and land pattern, retaining every other library entry.
lib=ROOT/'abx-symbols.kicad_sym';s=lib.read_text()
if '(symbol "TVS3300DRVR"' not in s:
    lib.write_text(s[:s.rfind(')')]+tvs3300_symbol()+'\n)\n')
fp=p.FootprintLoad('/usr/share/kicad/footprints/Package_SON.pretty',
    'WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm')
fp.SetFPID(p.LIB_ID(*TVS_FP.split(':')));fp.SetValue('TVS3300DRVR')
fp.SetLibDescription('TI TVS3300 DRV0006A; SLVSDO2C land pattern: 0.45x0.30mm pins, 1.95mm row centres, EP 1x1.6mm')
for q in fp.Pads():
    if q.GetNumber() in ['1','2','3','4','5','6']:
        pos=q.GetPosition();pos.x=p.FromMM(-.975 if q.GetNumber() in ['1','2','3'] else .975)
        q.SetPosition(pos);q.SetSize(p.VECTOR2I(p.FromMM(.45),p.FromMM(.3)))
        q.SetRoundRectRadiusRatio(.05/.3)
fp.SetField('LCSC',TVS_SKU);fp.GetField('LCSC').SetVisible(False);fp.Value().SetVisible(False)
p.FootprintSave(str(ROOT/'abx-footprints.pretty'),fp)

# Remove only the former D2 symbol and its two individual power stubs.
power=(ROOT/'Power.kicad_sch').read_text()
oldblock=next(bl for a,z,bl in blocks(power,'symbol') if '(property "Reference" "D2"' in bl)
oldtree=g.parse_sexp(oldblock)
old_uuid=node(oldtree,'uuid')[1][1]
probe=g.SchematicBuilder('Power.kicad_sch',g.SymbolLibraryCache(),[],paper='A3')
probe_sym=probe.place_sym('Device:D_TVS','D2','SMCJ30A','Diode_SMD:D_SMC',142.24,71.12,270)
pincoords={(v['x'],v['y']) for v in probe_sym['pins'].values()}
remove=[];power_ends=set()
for a,z,bl in blocks(power,'wire'):
    tree=g.parse_sexp(bl);pts=node(tree,'pts')
    coords=[tuple(float(v[1]) for v in child[1:3]) for child in pts[1:]]
    if pincoords.intersection(coords):
        remove.append((a,z));power_ends.update(set(coords)-pincoords)
assert len(remove)==2,(pincoords,remove)
for a,z,bl in blocks(power,'symbol'):
    tree=g.parse_sexp(bl)
    if bl==oldblock or ('(lib_id "power:' in bl and at(tree) in power_ends):remove.append((a,z))
assert len(remove)==5,len(remove)
for a,z in sorted(remove,reverse=True):power=power[:a]+power[z:]
g.SchematicBuilder.pwr_counter=9100
cache=g.SymbolLibraryCache()
sb=g.SchematicBuilder('Power.kicad_sch',cache,[(f'/{g.ROOT_UUID}/{g.SHEET_UUIDS["Power"]}',0)],paper='A3')
place_tvs3300(sb)
sb.symbols[0]=re.sub(r'\(uuid "[^"]+"\)',f'(uuid "{old_uuid}")',sb.symbols[0],count=1)
sb.add_text('D2: 33V standoff; 40V max at specified 8/20us pulse. No continuous braking-energy rating.',25.4,27.94,1.27)
flat,_=cache.get_symbol_and_pins('abx:TVS3300DRVR')
liba,libz,libblock=next(blocks(power,'lib_symbols'))
newlib=libblock[:libblock.rfind(')')]+g.format_sexp(flat,2)+'\n\t)'
power=power[:liba]+newlib+power[libz:]
fragment='\n'.join(sb.texts+sb.junctions+sb.wires+sb.symbols)
power=power[:power.rfind(')')]+fragment+'\n)\n'
(ROOT/'Power.kicad_sch').write_text(power)

b=p.LoadBoard(str(ROOT/'abx-motion.kicad_pcb'))
old=b.FindFootprintByReference('D2');assert old.GetValue()=='SMCJ30A'
f=p.FootprintLoad(str(ROOT/'abx-footprints.pretty'),TVS_FP.split(':')[1])
f.SetFPID(p.LIB_ID(*TVS_FP.split(':')))
f.SetParent(b);f.SetReference('D2');f.SetPosition(old.GetPosition());f.SetOrientationDegrees(180)
f.SetPath(old.GetPath());f.SetUuid(old.m_Uuid)
f.Reference().SetPosition(p.VECTOR2I(p.FromMM(182),p.FromMM(61.5)))
f.Reference().SetTextSize(p.VECTOR2I(p.FromMM(.7),p.FromMM(.7)))
f.Reference().SetTextThickness(p.FromMM(.12))
for q in f.Pads():
    if q.GetNumber():q.SetNet(b.FindNet('+BATT' if q.GetNumber() in ['4','5','6'] else 'GND'))
b.Remove(old);b.Add(f)
pt=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def track(net,a,z,w):
    t=p.PCB_TRACK(b);t.SetStart(pt(*a));t.SetEnd(pt(*z));t.SetWidth(p.FromMM(w))
    t.SetLayer(p.F_Cu);t.SetNet(b.FindNet(net));b.Add(t)
# Fan all three IN pins into the old power landing. EP and GND pins share a
# short wide return to the old ground landing plus three local plane vias.
track('+BATT',(178.6,63.5),(180.35,63.5),1.0)
track('+BATT',(180.35,62.85),(180.35,64.15),.8)
for y in [62.85,63.5,64.15]:track('+BATT',(180.35,y),(181.025,y),.3)
track('GND',(182,63.5),(185.4,63.5),.8)
track('GND',(183.5,62.85),(183.5,64.15),.65)
for y in [62.85,63.5,64.15]:track('GND',(182.975,y),(183.5,y),.3)
for x,y in [(183.7,62.85),(183.7,64.15),(184.6,63.5)]:
    track('GND',(183.5,y),(x,y),.45)
    v=p.PCB_VIA(b);v.SetPosition(pt(x,y));v.SetWidth(p.FromMM(.65));v.SetDrill(p.FromMM(.3))
    v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet('GND'));b.Add(v)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(ROOT/'abx-motion.kicad_pcb'),b)
(OUT/'clamp-changes.json').write_text(json.dumps({
    'reference':'D2','before':'SMCJ30A/C310046','after':'TVS3300DRVR/'+TVS_SKU,
    'footprint':TVS_FP,'position_mm':[182,63.5],'rotation_deg':180,
    'pin_map':{'1':'GND','2':'GND','3':'GND','4':'+BATT','5':'+BATT','6':'+BATT','7':'GND'},
    'rating_scope':'33V standoff; 40V max at 35A 8/20us per TI; DRV package 3.5A 10/1000us. Not continuous regen protection.',
    'land_pattern_source':'TI DRV0006A, SLVSDO2C page 22'},indent=2)+'\n')
print('D2 local pulse clamp saved; fresh checks required.')
