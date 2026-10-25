"""Deterministic KiCad 10 hierarchical-sheet generator: embeds lib symbols, places parts, labels pin ends."""
import re, sys, uuid, os
sys.path.insert(0, os.path.dirname(__file__)); import sx
KICAD = '/usr/share/kicad/symbols'
PROJ = '/home/mark/Documents/abx-motion'
LIBS = {'abx': f'{PROJ}/abx-symbols.kicad_sym'}
NS = uuid.UUID('6f1c1d52-0c3a-4d0a-9c53-5c0e9d1b7a11')
GRID = 1.27
def uid(*k): return str(uuid.uuid5(NS, '|'.join(map(str, k))))
def snap(v): return round(round(v / GRID) * GRID, 2)
def fmt(v): return ('%.2f' % v).rstrip('0').rstrip('.')

def upgrade(b):
    """KiCad 7 library text -> KiCad 10 embedded-symbol syntax (so ERC does not flag lib_symbol_mismatch)."""
    b = re.sub(r'\(pin_numbers hide\)', '(pin_numbers (hide yes))', b)
    b = re.sub(r'\(pin_names \(offset ([\d.]+)\) hide\)', r'(pin_names (offset \1) (hide yes))', b)
    b = re.sub(r'\(pin_names hide\)', '(pin_names (hide yes))', b)
    b = re.sub(r'(\(effects\s*\(font\s*\(size [\d.]+ [\d.]+\)(?:\s*\(thickness [\d.]+\))?(?:\s*(?:bold|italic))*\s*\)(?:\s*\(justify [^)]*\))?)\s+hide\s*\)', r'\1 (hide yes))', b)
    b = re.sub(r'(\(length [\d.]+\))\s+hide\b', r'\1 (hide yes)', b)
    b = b.replace('"ki_description"', '"Description"')
    if '(exclude_from_sim' not in b.split('(symbol "', 2)[1] if b.count('(symbol "') > 1 else True:
        b = b.replace('(in_bom', '(exclude_from_sim no) (in_bom', 1)
    # canonical property order + trailing (embedded_fonts no), as KiCad 10 writes embedded symbols
    ch = sx.spans(b, 1)
    props = [(s, e, b[s:e]) for s, e, h in ch if h == 'property']
    if props:
        order = {'Reference': 0, 'Value': 1, 'Footprint': 2, 'Datasheet': 3, 'Description': 4, 'ki_keywords': 5, 'ki_fp_filters': 6}
        key = lambda pr: order.get(re.match(r'\(property "([^"]+)"', pr[2]).group(1), 9)
        srt = sorted(props, key=key)
        first, last = props[0][0], props[-1][1]
        b = b[:first] + '\n\t\t'.join(x[2] for x in srt) + b[last:]
    if '(embedded_fonts' not in b[-40:]:
        b = b[:-1].rstrip() + '\n\t\t(embedded_fonts no)\n\t)'
    return b
_cache = {}
def _block(lib, name):
    path = LIBS.get(lib, f'{KICAD}/{lib}.kicad_sym')
    t = open(path).read()
    for s, e, h in sx.spans(t):
        if h == 'symbol' and t[s:e].startswith('(symbol "%s"' % name): return t[s:e]
    raise KeyError(f'{lib}:{name}')
def load(lib, name):
    """-> (embedded block text 'Lib:Name', pins {number: (name, x, y, angle)})"""
    key = (lib, name)
    if key in _cache: return _cache[key]
    b = _block(lib, name)
    m = re.search(r'\(extends "([^"]+)"\)', b)
    if m:
        parent = m.group(1); pb = _block(lib, parent)
        pb = pb.replace('(symbol "%s"' % parent, '(symbol "%s"' % name, 1)
        pb = re.sub(r'\(symbol "%s_(\d+)_(\d+)"' % re.escape(parent), r'(symbol "%s_\1_\2"' % name, pb)
        for pn in ('Reference', 'Value', 'Footprint', 'Datasheet', 'Description'):
            v = sx.prop(b, pn)
            if v is not None:
                pb = re.sub(r'(\(property "%s" ")((?:[^"\\]|\\.)*)(")' % pn, lambda mm: mm.group(1) + v + mm.group(3), pb, count=1)
        b = pb
    emb = upgrade(b.replace('(symbol "%s"' % name, '(symbol "%s:%s"' % (lib, name), 1))
    pins = {}
    for pm in re.finditer(r'\(pin (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s*\(length ([\d.]+)\)(.*?)\(name "([^"]*)".*?\(number "([^"]*)"', b, re.S):
        pins[pm.group(9)] = (pm.group(8), float(pm.group(3)), float(pm.group(4)), int(pm.group(5)), pm.group(2))
    _cache[key] = (emb, pins)
    return _cache[key]

class Sheet:
    def __init__(self, paper='A2', root_uuid='', sheet_uuids=(), project='abx-motion-brushless', globals_=('GND', '+5V', 'VBUS')):
        self.parts = []; self.labels = []; self.texts = []; self.ncs = []; self.paper = paper
        self.root = root_uuid; self.sheets = sheet_uuids; self.project = project; self.globals = set(globals_)
        self.used = {}      # ref -> set(pins connected)
        self.libs = {}      # 'lib:name' -> emb
        self.hier = []; self.hier_shapes = {}
        self.uuids = {}     # ref -> existing symbol uuid (keeps PCB links when a sheet is regenerated)
        self.fields = {}    # ref -> {name: value}: extra hidden fields (e.g. LCSC), rendered after Description
    def add(self, ref, sym, value, fp, x, y, nets=None, nc=(), hide_value=False):
        lib, name = sym.split(':', 1)
        emb, pins = load(lib, name); self.libs[sym] = emb
        x, y = snap(x), snap(y); nets = nets or {}
        # resolve names -> numbers
        byname = {}
        for num, (pn, *_r) in pins.items(): byname.setdefault(pn, []).append(num)
        res = {}
        for k, net in nets.items():
            if k in pins: res[k] = net
            elif k in byname and len(byname[k]) == 1: res[byname[k][0]] = net
            else: raise KeyError(f'{ref}: pin {k} ambiguous/unknown in {sym} ({list(byname)})')
        ncn = []
        for k in nc:
            if k in pins: ncn.append(k)
            elif k in byname: ncn += byname[k]
            else: raise KeyError(f'{ref}: nc pin {k}')
        self.parts.append(dict(ref=ref, sym=sym, value=value, fp=fp, x=x, y=y, pins=pins, hide_value=hide_value))
        self.used[ref] = set(res) | set(ncn)
        for num, net in res.items():
            _, px, py, ang, _t = pins[num]
            self.label(net, x + px, y - py, (ang + 180) % 360)
        for num in ncn:
            _, px, py, ang, _t = pins[num]
            self.ncs.append((x + px, y - py))
        return ref
    def label(self, net, x, y, rot):
        x, y = round(x, 2), round(y, 2)
        if net.startswith('hier:'): self.hier.append((net[5:], x, y, rot))
        else: self.labels.append(('global_label' if net in self.globals else 'label', net, x, y, rot))
    def text(self, s, x, y, size=1.27, bold=False):
        self.texts.append((s, x, y, size, bold))
    def check(self, autonc=()):
        """every pin of every part must be connected or NC; autonc refs get NC on the rest."""
        for p in self.parts:
            miss = [n for n in p['pins'] if n not in self.used[p['ref']]]
            if miss and p['ref'] in autonc:
                for n in miss:
                    _, px, py, ang, _t = p['pins'][n]; self.ncs.append((p['x'] + px, p['y'] - py)); self.used[p['ref']].add(n)
            elif miss: raise ValueError(f"{p['ref']} unconnected pins {miss} ({[p['pins'][n][0] for n in miss]})")
    def _eff(self, size=1.27, extra='', hide=False):
        return f'(effects (font (size {size} {size})){extra}{" (hide yes)" if hide else ""})'
    def render(self, instances):
        """instances: list of (sheet_path, ref_offset)"""
        o = ['(kicad_sch', '\t(version 20250114)', '\t(generator "eeschema")', '\t(generator_version "10.0")',
             f'\t(uuid "{uid("sheet", self.project, self.paper)}")', f'\t(paper "{self.paper}")', '\t(lib_symbols']
        for emb in self.libs.values():
            o.append('\t\t' + emb.replace('\n', '\n\t'))
        o.append('\t)')
        for s, x, y, size, bold in self.texts:
            o.append(f'\t(text "{s}"\n\t\t(exclude_from_sim no)\n\t\t(at {fmt(x)} {fmt(y)} 0)\n\t\t(effects (font (size {size} {size}){" (bold yes)" if bold else ""}) (justify left bottom))\n\t\t(uuid "{uid("text", s, x, y)}")\n\t)')
        for x, y in self.ncs: o.append(f'\t(no_connect (at {fmt(x)} {fmt(y)}) (uuid "{uid("nc", x, y)}"))')
        for kind, net, x, y, rot in self.labels:
            just = {0: 'left bottom', 180: 'right bottom'}.get(rot, 'left bottom') if kind == 'label' else ('right' if rot == 180 else 'left')
            extra = '' if kind == 'label' else ''
            o.append(f'\t({kind} "{net}"\n\t\t(at {fmt(x)} {fmt(y)} {rot})\n\t\t(effects (font (size 1.27 1.27)) (justify {just}))\n\t\t(uuid "{uid(kind, net, x, y)}")\n\t)')
        for net, x, y, rot in self.hier:
            o.append(f'\t(hierarchical_label "{net}"\n\t\t(shape {self.hier_shapes.get(net, "bidirectional")})\n\t\t(at {fmt(x)} {fmt(y)} {rot})\n\t\t(effects (font (size 1.27 1.27)) (justify {"right" if rot == 180 else "left"}))\n\t\t(uuid "{uid("hier", net, x, y)}")\n\t)')
        def refnum(ref, off):
            m = re.match(r'^([A-Za-z_]+)(\d+)$', ref)
            return f'{m.group(1)}{int(m.group(2)) + off}' if m else ref
        for p in self.parts:
            x, y = p['x'], p['y']
            xs = [x + v[1] for v in p['pins'].values()]; ys = [y - v[2] for v in p['pins'].values()]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            small = len(p['pins']) <= 3
            if small: rx, ry, vx, vy, j = x + 2.54, y - 1.27, x + 2.54, y + 1.27, '(justify left)'
            else: rx, ry, vx, vy, j = cx, cy - 2.54, cx, cy + 2.54, ''
            props = [('Reference', p['ref'], rx, ry, False, j), ('Value', p['value'], vx, vy, p['hide_value'], j),
                     ('Footprint', p['fp'], x, y, True, ''), ('Datasheet', '', x, y, True, ''), ('Description', '', x, y, True, '')]
            props += [(n, v, x, y, True, '') for n, v in self.fields.get(p['ref'], {}).items()]
            ps = ''.join(f'\n\t\t(property "{n}" "{v}"\n\t\t\t(at {fmt(px)} {fmt(py)} 0)\n\t\t\t(effects (font (size 1.27 1.27)){" " + jj if jj else ""}{" (hide yes)" if h else ""})\n\t\t)' for n, v, px, py, h, jj in props)
            pn = ''.join(f'\n\t\t(pin "{n}"\n\t\t\t(uuid "{uid("pin", p["ref"], n)}")\n\t\t)' for n in p['pins'])
            inst = ''.join(f'\n\t\t\t\t(path "{path}"\n\t\t\t\t\t(reference "{refnum(p["ref"], off)}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)' for path, off in instances)
            o.append(f'\t(symbol\n\t\t(lib_id "{p["sym"]}")\n\t\t(at {fmt(x)} {fmt(y)} 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "{self.uuids.get(p["ref"]) or uid("sym", p["ref"])}"){ps}{pn}\n\t\t(instances\n\t\t\t(project "{self.project}"{inst}\n\t\t\t)\n\t\t)\n\t)')
        o.append('\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)')
        return '\n'.join(o) + '\n'

def existing_uuids(path):
    """ref -> symbol uuid of a sheet file (first instance reference)."""
    t = open(path).read(); out = {}
    for s, e, h in sx.spans(t, 1):
        if h == 'symbol':
            b = t[s:e]; m = re.search(r'\n\t\t\(uuid "([^"]+)"\)', b) or re.search(r'\(uuid "([^"]+)"\)', b)
            out[sx.prop(b, 'Reference')] = m.group(1)
    return out

def inject(target, rendered):
    """Merge a rendered Sheet (lib symbols + items) into an existing sheet text."""
    top = sx.spans(rendered, 1)
    lib = [x for x in top if x[2] == 'lib_symbols'][0]
    sub = rendered[lib[0]:lib[1]]
    libs = [sub[s:e] for s, e, h in sx.spans(sub, 1) if h == 'symbol']
    body = [rendered[s:e] for s, e, h in top if h in ('symbol', 'label', 'global_label', 'hierarchical_label', 'no_connect', 'text', 'wire', 'junction')]
    tl = [x for x in sx.spans(target, 1) if x[2] == 'lib_symbols'][0]
    have = set(re.findall(r'\n\t\t\(symbol "([^"]+)"', target[tl[0]:tl[1]]))
    add = ''.join('\t\t' + b.replace('\n', '\n\t') + '\n' for b in libs if re.match(r'\(symbol "([^"]+)"', b).group(1) not in have)
    i = target.rfind(')', tl[0], tl[1]); i = target.rfind('\n', 0, i) + 1
    target = target[:i] + add + target[i:]
    ends = [s for s, e, h in sx.spans(target, 1) if h in ('sheet_instances', 'embedded_fonts')]
    j = target.rfind('\n', 0, min(ends)) + 1
    return target[:j] + ''.join('\t' + b + '\n' for b in body) + target[j:]
