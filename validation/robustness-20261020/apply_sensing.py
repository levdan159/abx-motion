"""Apply only the reviewed local sensing changes; preserve existing routing."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import re
import sys
import pcbnew as p

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BEFORE = OUT / 'before'
sys.path.insert(0, str(ROOT))
import generate_schematics as g

def top_blocks(s, name):
    # Match exact top-level s-expressions without reformatting the source.
    depth = 0
    start = None
    for m in re.finditer(r'"(?:\\.|[^"\\])*"|\(|\)', s):
        if m.group() == '(':
            if depth == 1:
                start = m.start()
            depth += 1
        elif m.group() == ')':
            depth -= 1
            if depth == 1 and start is not None:
                block = s[start:m.end()]
                if re.match(r'\(' + re.escape(name) + r'(?:\s|\))', block):
                    yield start, m.end(), block

def set_value(s, ref, old, new):
    found = 0
    for a, z, block in list(top_blocks(s, 'symbol'))[::-1]:
        if re.search(r'\(property "Reference" "' + re.escape(ref) + '"', block):
            assert f'(property "Value" "{old}"' in block
            block = block.replace(f'(property "Value" "{old}"', f'(property "Value" "{new}"')
            s = s[:a] + block + s[z:]
            found += 1
    assert found == 1, (ref, found)
    return s

power = (BEFORE / 'Power.kicad_sch').read_text()
power = set_value(power, 'R2', '100k', '150k')
power = set_value(power, 'R6', '10k', '22k')
(ROOT / 'Power.kicad_sch').write_text(power)

# Append one resistor symbol instantiated once in each existing motor sheet.
g.SchematicBuilder.pwr_counter = 9000
cache = g.SymbolLibraryCache()
sb = g.SchematicBuilder('Motor_Channel.kicad_sch', cache,
    [(f'/{g.ROOT_UUID}/{g.SHEET_UUIDS["Motor1"]}', 0),
     (f'/{g.ROOT_UUID}/{g.SHEET_UUIDS["Motor2"]}', 1)], paper='A3')
symbol = sb.place_sym('Device:R', 'R313', '1k', 'Resistor_SMD:R_0603_1608Metric',
    254, 175.26, 0, alt_refs={0: 'R313', 1: 'R413'})
sb.stub_net(symbol, '1', 'CS')
sb.stub_power(symbol, '2', 'GND')
sb.add_text('ADC protection: R304/R404 + R313/R413 divide SO by 2; rescale firmware.',
    193.04, 187.96, 1.27)
fragment = '\n'.join(sb.texts + sb.wires + sb.labels + sb.symbols)
motor = (BEFORE / 'Motor_Channel.kicad_sch').read_text()
assert '"R313"' not in motor
motor = motor[:motor.rfind(')')] + fragment + '\n)\n'
(ROOT / 'Motor_Channel.kicad_sch').write_text(motor)
new_symbol_uuid = re.search(r'\(uuid "([^"]+)"\)', sb.symbols[0]).group(1)

board = p.LoadBoard(str(BEFORE / 'abx-motion.kicad_pcb'))
fps = {f.GetReference(): f for f in board.GetFootprints()}
for ref, value, sku in [('R2', '150k', 'C22807'), ('R6', '22k', 'C31850')]:
    fps[ref].SetValue(value)
    fps[ref].GetField('LCSC').SetText(sku)
    fps[ref].Value().SetVisible(False)

def pt(x, y):
    return p.VECTOR2I(p.FromMM(round(x, 5)), p.FromMM(round(y, 5)))

def track(net, start, end, width=.22, layer=p.F_Cu):
    if start == end:
        return
    t = p.PCB_TRACK(board)
    t.SetStart(pt(*start)); t.SetEnd(pt(*end)); t.SetWidth(p.FromMM(width))
    t.SetLayer(layer); t.SetNet(board.FindNet(net)); board.Add(t)

changes = []
sites=json.loads((OUT/'local-sites.json').read_text())
for idx, (ref, cs) in enumerate([('R313', '/M1_CS'), ('R413', '/M2_CS')]):
    site=sites[ref]
    x,y=site['xy']
    f = p.Cast_to_FOOTPRINT(fps['R304'].Duplicate(False))
    f.SetUuid(p.KIID())
    f.SetParent(board)
    f.SetReference(ref)
    f.SetPosition(pt(x, y))
    f.SetOrientationDegrees(site['angle'])
    f.SetPath(p.KIID_PATH('/' + g.SHEET_UUIDS['Motor1' if idx == 0 else 'Motor2'] + '/' + new_symbol_uuid))
    f.Value().SetVisible(False)
    f.GetField('LCSC').SetVisible(False)
    f.Reference().SetPosition(pt(171,91.4) if ref=='R313' else pt(154.2,101.5))
    f.Reference().SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T))
    f.Reference().SetTextSize(pt(.7, .7))
    f.Reference().SetTextThickness(p.FromMM(.12))
    for pad in f.Pads():
        pad.SetUuid(p.KIID())
        pad.SetNet(board.FindNet(cs if pad.GetNumber() == '1' else 'GND'))
    board.Add(f)
    # Short local branches into existing CS vias; preserve every old segment.
    track(cs, site['signal_pad'], site['signal_via'])
    track('GND', site['ground_pad'], site['ground_via'])
    for start,end in zip(site['B_Cu_path'],site['B_Cu_path'][1:]):
        track(cs,start,end,layer=p.B_Cu)
    for net,key in [(cs,'signal_via'),('GND','ground_via')]:
        via = p.PCB_VIA(board)
        via.SetPosition(pt(*site[key])); via.SetWidth(p.FromMM(.6)); via.SetDrill(p.FromMM(.3))
        via.SetLayerPair(p.F_Cu, p.B_Cu); via.SetNet(board.FindNet(net)); board.Add(via)
    changes.append({'reference': ref, 'position_mm': [x, y], 'value': '1k', 'LCSC': 'C21190'})

board.BuildConnectivity()
p.ZONE_FILLER(board).Fill(board.Zones())
p.SaveBoard(str(ROOT / 'abx-motion.kicad_pcb'), board)
(OUT / 'sensing-changes.json').write_text(json.dumps({
    'added': changes, 'value_changes': {'R2': ['100k', '150k'], 'R6': ['10k', '22k']},
    'base_PCB_sha256': hashlib.sha256((BEFORE/'abx-motion.kicad_pcb').read_bytes()).hexdigest(),
    'new_symbol_UUID': new_symbol_uuid}, indent=2) + '\n')
print('Local sensing edits saved; run fresh ERC/DRC before packaging.')
