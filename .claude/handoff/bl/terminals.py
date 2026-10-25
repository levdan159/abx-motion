"""Edge terminals: phases J301-J303 / J401-J403 -> Wurth REDCUBE M4 74650074 (50 A), battery J1 -> 2x REDCUBE M5 74655095.
Footprint-only swap (symbols and nets unchanged). Run with the schematic editor closed; then F8 with
'Replace footprints with those specified in the schematic' ticked."""
import os
P = os.path.expanduser('~/Documents/abx-motion')
SWAPS = {
    'ESC_Channel.kicad_sch': [('"Connector_Wire:SolderWirePad_1x01_SMD_5x10mm"', '"TerminalBlock_Wuerth:Wuerth_REDCUBE-THR_WP-THRBU_74650074_THR"', 3)],
    'Power.kicad_sch': [('"abx-footprints:ABX_BatteryPads_1x02_SMD_10x14mm_P14mm"', '"abx-footprints:ABX_REDCUBE_M5_x2_P18mm"', 1),
                        ('(property "Value" "BATTERY_IN"', '(property "Value" "BATTERY_IN 2x WE 74655095 M5"', 1)],
}
for f, reps in SWAPS.items():
    t = open(f'{P}/{f}').read()
    for old, new, n in reps:
        assert t.count(old) == n, (f, old, t.count(old)); t = t.replace(old, new)
    open(f'{P}/{f}', 'w').write(t); print('updated', f)
