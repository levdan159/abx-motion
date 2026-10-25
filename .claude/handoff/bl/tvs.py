"""Add the VBUS TVS (D301 / D401, one per power stage, at the bus caps) to ESC_Channel.kicad_sch.
Not idempotent: refuses to run when D301 is already there.  python tvs.py [out_path]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from schgen import Sheet, inject
from esc2_ids import ROOT, S1, S2  # noqa: E402  (same instance paths esc2.py renders with)
P = os.path.expanduser('~/Documents/abx-motion/ESC_Channel.kicad_sch')
OUT = sys.argv[1] if len(sys.argv) > 1 else P
t = open(P).read()
assert '"D301"' not in t, 'D301 already in ESC_Channel'
sh = Sheet(paper='A2', globals_=('GND', '+5V', 'VBUS', '+3V3_ESC'))
sh.add('D301', 'Device:D_TVS', 'SMCJ43A', 'Diode_SMD:D_SMC', 540, 128, {'1': 'VBUS', '2': 'GND'})
sh.check()
t = inject(t, sh.render([(f'/{ROOT}/{S1}', 0), (f'/{ROOT}/{S2}', 100)]))
OLD = 'no TVS clamping above ~65 V on VBUS.'
NEW = ('D301 SMCJ43A TVS on VBUS (one per stage): ~54 V at a few A, 69 V at full current, so it only trims regen spikes; '
       'the real limit is VESC max input voltage 46-48 V (regen stops before the breaker can strand the energy).')
assert OLD in t; t = t.replace(OLD, NEW)
open(OUT, 'w').write(t); print('wrote', OUT)
