"""Greedy copper-aware placement of the staged parts (search tool; its output poses go into bl/newplace.py).
usage: greedy.py <in.kicad_pcb> <spec.py> <out.json> [variant]
spec.py defines STEPS(variant) -> list of steps:
  ('fix', ref, x, y, rot)                      pose as given (checked, reported)
  ('block', name, {ref: (x, y, rot)})          template block from tsearch.py (checked)
  ('near', ref, [(pad, target), ...], win, rots[, home])
        target = 'REF.PAD' (that pad's centre, after earlier steps) or (x, y); win = (x0, y0, x1, y1) for the part
        centre; cost = sum of pad-to-target distances (+ 0.05 x distance to home if given); first legal pose wins."""
import sys, json, math, runpy
import numpy as np
import pcbnew
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from engine import Occ, pose, MM

b = pcbnew.LoadBoard(sys.argv[1]); fp = {f.GetReference(): f for f in b.GetFootprints()}
variant = sys.argv[4] if len(sys.argv) > 4 else 'real'
steps = runpy.run_path(sys.argv[2])['STEPS'](variant)
moving = set()
import copy as _copy
_snap = {}
def occ_snapshot():
    _snap['F'] = occ.F.copy(); _snap['B'] = occ.B.copy(); _snap['C'] = occ.C.copy()
def occ_restore():
    occ.F[:] = _snap['F']; occ.B[:] = _snap['B']; occ.C[:] = _snap['C']

def legal(ref, legs, win, rots, home):
    """yield (cost, x, y, rot) of legal poses, cheapest first (part left at the last yielded pose)"""
    f = fp[ref]; legs = [(str(p), tgt(t)) for p, t in legs]
    xs = np.arange(win[0], win[2] + 1e-6, 0.25); ys = np.arange(win[1], win[3] + 1e-6, 0.25)
    X, Y = np.meshgrid(xs, ys); cands = []
    for r in rots:
        pose(f, 0, 0, r)
        offs = [(padc(ref, p), t) for p, t in legs]
        C = np.zeros_like(X)
        for (ox, oy), (tx, ty) in offs: C += np.hypot(X + ox - tx, Y + oy - ty)
        if home: C += 0.05 * np.hypot(X - home[0], Y - home[1])
        cands += list(zip(C.ravel(), X.ravel(), Y.ravel(), [r] * C.size))
    cands.sort()
    for c, x, y, r in cands[:60000]:
        pose(f, x, y, r)
        if not occ.check(f): yield (c, x, y, r)

for s in steps:
    if s[0] == 'block': moving |= set(s[2])
    elif s[0] == 'pair': moving |= {s[1], s[3]}
    else: moving.add(s[1])
occ = Occ(b, moving=moving)
out, problems = {}, []

def padc(ref, num):
    qs = [q for q in fp[ref].Pads() if q.GetNumber() == str(num)]
    qs.sort(key=lambda q: -q.GetBoundingBox().GetWidth() * q.GetBoundingBox().GetHeight())
    p = qs[0].GetPosition(); return p.x / MM, p.y / MM

def tgt(t):
    if isinstance(t, str):
        r, n = t.split('.'); return padc(r, n)
    return t

for s in steps:
    if s[0] in ('fix', 'block'):
        items = {s[1]: s[2:5]} if s[0] == 'fix' else s[2]
        for ref, (x, y, r) in items.items():
            pose(fp[ref], x, y, r)
        for ref in items:
            bad = occ.check(fp[ref])
            if bad: problems.append((ref, bad)); print('PROBLEM', ref, bad)
            out[ref] = list(items[ref])
        for ref in items: occ.add_fp(fp[ref])
        continue
    if s[0] == 'pair':
        _, ra, la, rb, lb, win, rots = s
        best = None; tried = 0
        for ca in legal(ra, la, win, rots, None):
            tried += 1
            if tried > 400 or (best and ca[0] >= best[0]): break
            sv = (occ.F.copy(), occ.B.copy(), occ.C.copy())
            occ.add_fp(fp[ra])
            cb = next(legal(rb, lb, (ca[1] - 5, ca[2] - 5, ca[1] + 5, ca[2] + 5), rots, None), None)
            occ.exact.pop(); occ.F[:], occ.B[:], occ.C[:] = sv
            pose(fp[ra], ca[1], ca[2], ca[3])
            if cb and (best is None or ca[0] + cb[0] < best[0]): best = (ca[0] + cb[0], ca, cb)
        if best is None: problems.append((ra, 'pair: no legal pose')); print('FAIL pair', ra); continue
        for r_, c_ in ((ra, best[1]), (rb, best[2])):
            pose(fp[r_], c_[1], c_[2], c_[3]); occ.add_fp(fp[r_]); out[r_] = [round(float(c_[1]), 3), round(float(c_[2]), 3), c_[3]]
            print(f'{r_:6s} ({c_[1]:7.2f},{c_[2]:7.2f}) r{c_[3]:3d}  cost {c_[0]:6.2f}  (pair)')
        continue
    _, ref, legs, win, rots = s[:5]; home = s[5] if len(s) > 5 else None
    f = fp[ref]; legs = [(str(p), tgt(t)) for p, t in legs]
    cands = []
    xs = np.arange(win[0], win[2] + 1e-6, 0.25); ys = np.arange(win[1], win[3] + 1e-6, 0.25)
    X, Y = np.meshgrid(xs, ys)
    for r in rots:
        pose(f, 0, 0, r)
        offs = [(padc(ref, p), t) for p, t in legs]
        C = np.zeros_like(X)
        for (ox, oy), (tx, ty) in offs: C += np.hypot(X + ox - tx, Y + oy - ty)
        if home: C += 0.05 * np.hypot(X - home[0], Y - home[1])
        for c, x, y in zip(C.ravel(), X.ravel(), Y.ravel()): cands.append((c, x, y, r))
    cands.sort()
    done = False
    for k, (c, x, y, r) in enumerate(cands):
        pose(f, x, y, r)
        if not occ.check(f):
            occ.add_fp(f); out[ref] = [round(float(x), 3), round(float(y), 3), r]; done = True
            print(f'{ref:6s} ({x:7.2f},{y:7.2f}) r{r:3d}  cost {c:6.2f}  (candidate {k})'); break
        if k > 60000: break
    if not done:
        problems.append((ref, 'no legal pose')); print('FAIL', ref)
json.dump({'poses': out, 'problems': [str(p) for p in problems]}, open(sys.argv[3], 'w'), indent=0)
b.Save(sys.argv[3].replace('.json', '.kicad_pcb'))
print('problems', len(problems))
