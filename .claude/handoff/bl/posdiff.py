"""Footprint position snapshot/diff against the LIVE editor (unsaved edits included).
  python posdiff.py snap [file]   save ref -> (x, y, rot, side)
  python posdiff.py diff [file]   list what moved / rotated / flipped since the snapshot"""
import json, sys
from kipy import KiCad
SNAP = sys.argv[2] if len(sys.argv) > 2 else '/home/mark/Documents/abx-motion/.claude/handoff/bak/pos_snapshot.json'

def now():
    out = {}
    for f in KiCad(timeout_ms=120000).get_board().get_footprints():
        p = f.position
        out[f.reference_field.text.value] = (round(p.x / 1e6, 2), round(p.y / 1e6, 2), round(f.orientation.degrees % 360, 1), f.layer)
    return out

if sys.argv[1] == 'snap':
    json.dump(now(), open(SNAP, 'w'), indent=0); print('snapshot', SNAP)
else:
    old, cur = json.load(open(SNAP)), now()
    for r in sorted(set(old) | set(cur)):
        a, c = old.get(r), cur.get(r)
        if a is None or c is None: print(r, 'ADDED' if a is None else 'REMOVED'); continue
        if tuple(a) != tuple(c):
            print(f'{r}: ({a[0]},{a[1]}) r{a[2]} -> ({c[0]},{c[1]}) r{c[2]}' + ('  FLIPPED' if a[3] != c[3] else ''))
