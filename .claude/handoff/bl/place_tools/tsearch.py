"""Find anchor poses for the TPS54360B blocks (U1, U901): TI DDA layout = the pattern buckplace.py used for U512
(same chip, tested: critical.py routed all its small-signal nets), offsets relative to the IC in its rot-0 frame."""
import sys, json, itertools
import numpy as np
import pcbnew
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from engine import Occ, pose, rel, MM

# (role, dx, dy, rot) in the IC's rot-0 frame; rot is the part's own rotation for an IC at rot 0
T = [('IC', 0, 0, 0),
     ('D', -0.1, -5.23, 180),      # catch diode above the IC: cathode (SW) over pin 8, anodes left by the CIN GND pads
     ('CBOOT', 4.85, -2.21, 270),  # between pin 8 and the inductor
     ('CHF', -4.6, -1.35, 90),     # 100 nF at pin 2 (VIN)
     ('CIN1', -7.6, -2.15, 90),    # 4.7 uF beside it
     ('CIN2', -11.2, -3.75, 270),  # second 4.7 uF further left (+BATT up)
     ('REN1', -4.95, 2.05, 90),    # UVLO top 0805: EN pad up beside pin 3
     ('REN2', -7.5, 1.55, 180),    # UVLO bottom: EN pad right
     ('RRT', -2.0, 4.38, 270),     # RT under pin 4
     ('RFB1', -0.4, 4.38, 90),     # FB top: Vout sense pad down
     ('RFB2', 1.2, 4.38, 270),     # FB bottom
     ('CHF2', 2.8, 4.38, 270),     # 68 pF COMP-GND
     ('RC', 4.4, 4.38, 270),       # Rcomp: COMP up, CZ down
     ('CZ', 4.6, 7.45, 270),       # 10 nF under Rcomp
     ('L', 10.2, -3.0, 0),         # 10 uH: SW pad (1) left by CBOOT / the diode cathode
     ('COUT1', 17.1, -4.6, 0),     # 47 uF: Vout pad left (L pad 1)
     ('COUT2', 17.1, -2.0, 0)]
MAP = {'U1': dict(IC='U1', D='D3', CBOOT='C6', CHF='C4', CIN1='C3', CIN2='C2', REN1='R12', REN2='R13', RRT='R10', RFB1='R4',
                  RFB2='R5', CHF2='C12', RC='R11', CZ='C11', L='L1', COUT1='C7', COUT2='C8'),
       'U901': dict(IC='U901', D='D902', CBOOT='C905', CHF='C903', CIN1='C902', CIN2='C901', REN1='R907', REN2='R908', RRT='R903',
                    RFB1='R901', RFB2='R902', CHF2='C911', RC='R904', CZ='C904', L='L901', COUT1='C906', COUT2='C907')}

def place_block(b, fp, blk, ax, ay, arot):
    out = {}
    for role, dx, dy, r in T:
        ref = MAP[blk][role]; x, y = rel(ax, ay, arot, dx, dy)
        pose(fp[ref], x, y, (r + arot) % 360); out[ref] = (round(x, 3), round(y, 3), (r + arot) % 360)
    return out

if __name__ == '__main__':
    b = pcbnew.LoadBoard(sys.argv[1]); fp = {f.GetReference(): f for f in b.GetFootprints()}
    blk, arot = sys.argv[2], int(sys.argv[3]); xr = [float(v) for v in sys.argv[4].split(',')]; yr = [float(v) for v in sys.argv[5].split(',')]
    tx, ty = float(sys.argv[6]), float(sys.argv[7])
    extra_keep = json.loads(sys.argv[8]) if len(sys.argv) > 8 else []
    refs = list(MAP[blk].values())
    occ = Occ(b, moving=refs)
    for k in extra_keep: occ.rect(occ.K, *k)
    # mutual courtyards of the block itself
    cands = sorted(itertools.product(np.arange(xr[0], xr[1] + 1e-6, 0.25), np.arange(yr[0], yr[1] + 1e-6, 0.25)),
                   key=lambda p: (p[0] - tx) ** 2 + (p[1] - ty) ** 2)
    best = None
    for n, (ax, ay) in enumerate(cands):
        place_block(b, fp, blk, ax, ay, arot)
        bad = {r: occ.check(fp[r]) for r in refs}
        bad = {r: v for r, v in bad.items() if v}
        if n == 0: print('at target', ax, ay, bad)
        if not bad:
            best = (ax, ay); break
    print('BEST', blk, best, 'tried', n + 1)
    if best:
        out = place_block(b, fp, blk, best[0], best[1], arot)
        # mutual courtyard overlap inside the block
        for a, c in itertools.combinations(refs, 2):
            A = fp[a].GetCourtyard(pcbnew.F_CrtYd); C = fp[c].GetCourtyard(pcbnew.F_CrtYd)
            s = pcbnew.SHAPE_POLY_SET(A); s.BooleanIntersection(C)
            if s.OutlineCount() and s.Area() > 0.001 * MM * MM: print('  self-overlap', a, c, round(s.Area() / MM / MM, 3))
        print(json.dumps(out))
