"""Regenerate ONLY ESC_Channel.kicad_sch from esc2.py (its first section).  python regen_esc_channel.py [out_path]"""
import os, sys
here = os.path.dirname(os.path.abspath(__file__)); src = open(os.path.join(here, 'esc2.py')).read()
W = "open(f'{P}/ESC_Channel.kicad_sch', 'w')"; i = src.index(W); j = src.index('\n', i)
out = sys.argv[1] if len(sys.argv) > 1 else None
code = src[:i] + (f"open({out!r}, 'w')" if out else W) + src[i + len(W):j] + '\n'
exec(compile(code, 'esc2_channel', 'exec'), {'__file__': os.path.join(here, 'esc2.py'), '__name__': '__main__'})
print('wrote', out or 'ESC_Channel.kicad_sch')
