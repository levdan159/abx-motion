"""Screw terminals (Degson DG135T-10.16, 57 A): ESC_Channel regenerated with one 3-pole J301 (PH_A/B/C) instead of
J301-J303; J1 footprint -> 2-pole DG135T. Run with KiCad closed; then F8 with 'Replace footprints' AND
'Delete footprints with no symbols' ticked (removes J302/J303/J402/J403)."""
import os, subprocess, sys
P = os.path.expanduser('~/Documents/abx-motion'); here = os.path.dirname(os.path.abspath(__file__))
subprocess.run([sys.executable, os.path.join(here, 'regen_esc_channel.py')], check=True, cwd=here)
t = open(f'{P}/Power.kicad_sch').read()
for old, new in (('"abx-footprints:ABX_REDCUBE_M5_x2_P18mm"', '"abx-footprints:ABX_Degson_DG135T-10.16-02P"'),
                 ('(property "Value" "BATTERY_IN 2x WE 74655095 M5"', '(property "Value" "BATTERY_IN DG135T-10.16-02P"')):
    assert t.count(old) == 1, old; t = t.replace(old, new)
open(f'{P}/Power.kicad_sch', 'w').write(t); print('updated Power.kicad_sch')
