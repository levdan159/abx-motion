"""Read the saved design; write review evidence only, never modify source or exports."""
from pathlib import Path
import collections
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
import pcbnew as p

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PROD = ROOT / 'production/final-bom-fix-20261020'
sha = lambda b: hashlib.sha256(b).hexdigest()
board = p.LoadBoard(str(ROOT / 'abx-motion.kicad_pcb'))
fps = {f.GetReference(): f for f in board.GetFootprints()}
xml = ET.parse(OUT / 'netlist.xml')
pn = {(n.get('ref'), n.get('pin')): net.get('name')
      for net in xml.findall('./nets/net') for n in net.findall('node')}
bp = {(f.GetReference(), pad.GetNumber()): pad.GetNetname()
      for f in fps.values() for pad in f.Pads() if pad.GetNumber()}
parity = [(ref, pin, name, bp.get((ref, pin)))
          for (ref, pin), name in pn.items() if bp.get((ref, pin)) != name]
assert not parity, parity
bom = list(csv.DictReader((PROD / 'abx-motion-jlcpcb-bom.csv').open()))
cpl = list(csv.DictReader((PROD / 'abx-motion-jlcpcb-cpl.csv').open()))
refs = [ref for row in bom for ref in row['Designator'].split(',')]
assert len(refs) == len(set(refs)) == len(cpl) == 237
assert set(refs) == {r['Designator'] for r in cpl}
field_errors = []
for row in bom:
    for ref in row['Designator'].split(','):
        base = ref[:-2] if ref in ['U501_L', 'U501_R', 'U502_L', 'U502_R'] else ref
        fields = {v.GetName(): v.GetText() for v in fps[base].GetFields()}
        if fields.get('LCSC') != row['LCSC Part #']:
            field_errors.append(ref)
assert not field_errors, field_errors
manifest = json.loads((PROD / 'manifest.json').read_text())
manifest_errors = [f for f, h in manifest.items() if sha((ROOT / f).read_bytes()) != h]
assert not manifest_errors, manifest_errors
gerber_zip = zipfile.ZipFile(PROD / 'abx-motion-gerbers.zip')
assert len(gerber_zip.namelist()) == 13
assert sorted(n for n in gerber_zip.namelist() if n.endswith('.drl')) == [
    'abx-motion-NPTH.drl', 'abx-motion-PTH.drl']
bundle = zipfile.ZipFile(PROD / 'abx-motion-review-bundle.zip')
bundle_pcb = [n for n in bundle.namelist() if n.endswith('/abx-motion.kicad_pcb') or n == 'abx-motion.kicad_pcb']
assert len(bundle_pcb) == 1
assert sha(bundle.read(bundle_pcb[0])) == sha((ROOT / 'abx-motion.kicad_pcb').read_bytes())

drc = json.loads((OUT / 'drc.json').read_text())
erc = json.loads((OUT / 'erc.json').read_text())
warnings = [v for v in drc['violations'] if v['severity'] == 'warning']
tracks = [v for v in board.GetTracks() if not isinstance(v, p.PCB_VIA)]
vias = [v for v in board.GetTracks() if isinstance(v, p.PCB_VIA)]
source_files = [f for f in manifest if not f.startswith('production/')]
hashes = {f: sha((ROOT / f).read_bytes()) for f in source_files}
audit = {
    'decision': 'HOLD for direct 7S battery use with a 32 V operating target',
    'review_scope': 'Static source, netlist, layout, package and datasheet review; no hardware tests or live JLC order access',
    'target': {'chemistry': 'Lithium ion, assumed conventional 4.2 V maximum per cell',
               'series_cells': 7, 'full_charge_V': 29.4, 'requested_operating_ceiling_V': 32,
               'battery_continuous_capability_A': 30,
               'motor_load_and_stepstick_model': 'Not supplied; battery capability is not board load'},
    'KiCad_version': p.Version(),
    'DRC_errors': sum(v['severity'] == 'error' for v in drc['violations']),
    'DRC_warnings': len(warnings),
    'DRC_warning_types': dict(collections.Counter(v['type'] for v in warnings)),
    'unconnected_items': len(drc.get('unconnected_items', [])),
    'schematic_parity_discrepancies': len(drc.get('schematic_parity', [])),
    'ERC_violations': sum(len(s.get('violations', [])) for s in erc['sheets']),
    'schematic_pins_matched_to_PCB': len(pn),
    'pin_parity_errors': parity,
    'BOM_groups': len(bom), 'BOM_unique_supplier_codes': len({r['LCSC Part #'] for r in bom}),
    'placements': len(cpl), 'BOM_CPL_references_match': True,
    'BOM_supplier_fields_match_saved_PCB': not field_errors,
    'all_package_manifest_hashes_match': not manifest_errors,
    'review_bundle_contains_current_PCB': True,
    'gerber_zip_files': gerber_zip.namelist(),
    'track_segments': len(tracks), 'vias': len(vias),
    'In1_signal_tracks': sum(t.GetLayer() == p.In1_Cu for t in tracks),
    'copper_layers': board.GetCopperLayerCount(),
    'stepper_net_widths_mm': {
        n: sorted({round(p.ToMM(t.GetWidth()), 4) for t in tracks if t.GetNetname() == n})
        for n in sorted({t.GetNetname() for t in tracks if 'STEP' in t.GetNetname()
                         and any(x in t.GetNetname() for x in ['_A1', '_A2', '_B1', '_B2'])})},
    'fuseholder_pad_drills_mm': [round(p.ToMM(pad.GetDrillSize().x), 4) for pad in fps['F1'].Pads()],
    'socket_drills_mm': sorted({round(p.ToMM(pad.GetDrillSize().x), 4)
                               for ref in ['U501', 'U502'] for pad in fps[ref].Pads()}),
    'calculations_nominal': {
        'VBAT_divider': {'upper_ohm': 100000, 'lower_ohm': 10000,
                         'ADC_at_29_4_V': 29.4 / 11, 'ADC_at_32_V': 32 / 11,
                         'ADC_at_48_4_V': 48.4 / 11,
                         'bus_at_3_6_V_ADC': 3.6 * 11},
        'proposed_VBAT_ratio_only_not_applied': {'upper_ohm': 150000, 'lower_ohm': 10000,
                                                'ADC_at_48_4_V': 48.4 / 16},
        'Q1_cold_loss_W_at_18_milliohm': {str(i): i*i*.018 for i in [5, 10, 15, 25, 30]},
        'AP2112_loss_W': {'at_0_3_A': (5-3.3)*.3, 'at_0_5_A': (5-3.3)*.5},
        'snubber_loss_W_at_32_V_20_kHz': 2.2e-9*32*32*20000,
        'R6_LED_resistor_W_at_32_V_assuming_2_1_V_LED': (32-2.1)**2/10000},
    'ADC_paths': {name: [{'ref': r, 'pin': pin} for (r, pin), n in pn.items() if n == name]
                  for name in ['/VBAT_SENSE', '/M1_CS', '/M2_CS', '/DC_Motor_1/SO_RAW', '/DC_Motor_2/SO_RAW']},
    'source_hashes': hashes,
    'electrical_source_or_upload_files_modified_by_review': False,
    'production_status_pointer_marked_HOLD': True
}
(OUT / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print(json.dumps({k: audit[k] for k in ['decision', 'DRC_errors', 'DRC_warnings',
    'ERC_violations', 'unconnected_items', 'schematic_parity_discrepancies',
    'schematic_pins_matched_to_PCB', 'BOM_groups', 'placements', 'track_segments', 'vias', 'In1_signal_tracks']}))
