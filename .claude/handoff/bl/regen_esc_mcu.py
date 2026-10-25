"""Regenerate ONLY ESC_MCU.kicad_sch from esc2.py (skips the ESC_Channel write, stops after ESC_MCU).  python regen_esc_mcu.py [out_path]"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__)); src = open(os.path.join(here, 'esc2.py')).read()
WC = "open(f'{P}/ESC_Channel.kicad_sch', 'w').write("; WM = "open(f'{P}/ESC_MCU.kicad_sch', 'w')"
src = src.replace(WC, "(lambda s: None)(", 1)
i = src.index(WM); j = src.index('\n', i)
out = sys.argv[1] if len(sys.argv) > 1 else None
code = src[:i] + (f"open({out!r}, 'w')" if out else WM) + src[i + len(WM):j] + '\n'
exec(compile(code, 'esc2_mcu', 'exec'), {'__file__': os.path.join(here, 'esc2.py'), '__name__': '__main__'})
print('wrote', out or 'ESC_MCU.kicad_sch')
