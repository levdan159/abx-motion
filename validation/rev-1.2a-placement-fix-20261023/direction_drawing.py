from pathlib import Path
import json
O=Path(__file__).resolve().parent;V=O.parent/'rev-1.2a-20261023';P=O.parents[1]/'production/rev-1.2a-20261023';rows={r['ref']:r for r in json.loads((V/'placements.json').read_text())};rules=json.loads((V/'orientation-rules.json').read_text());sc=5;X=lambda x:100+(x-45)*sc;Y=lambda y:85+(y-48)*sc
s=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="720" viewBox="0 0 1000 720"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#c23529"/></marker></defs><rect width="1000" height="720" fill="#fafafa"/><text x="30" y="30" font-size="21">Rev 1.2a — screw-terminal wire-entry direction / TOP VIEW</text><text x="30" y="55" font-size="14">Red arrows point OUTWARD from the wire opening. Rotations below are already applied in the corrected CPL.</text>',f'<rect x="{X(45)}" y="{Y(48)}" width="{157*sc}" height="{105*sc}" fill="#e5f0e9" stroke="#305640" stroke-width="3"/>']
for ref,(dx,dy) in rules['expected_wire_entry'].items():
 r=rows[ref];x,y=X(r['x']),Y(r['y']);s.append(f'<circle cx="{x}" cy="{y}" r="8" fill="#21733d"/><line x1="{x}" y1="{y}" x2="{x+dx*65}" y2="{y+dy*65}" stroke="#c23529" stroke-width="4" marker-end="url(#arrow)"/>')
 if dx==1:tx,ty=x-170,y-12
 elif dx==-1:tx,ty=x+15,y-12
 else:tx,ty=x-45,y-20
 s.append(f'<text x="{tx}" y="{ty}" font-size="15">{ref}: {r["rotation"]}°</text>')
s.append('<text x="30" y="660" font-size="14">C8465 (2 positions) supplier-zero entry: -Y. C72334 (3 positions) supplier-zero entry: +Y.</text><text x="30" y="685" font-size="14">Pad-number equality alone is insufficient: C8465 independent terminal contact numbers are intentionally reversed.</text></svg>');(P/'assembly/terminal-wire-entry.svg').write_text(''.join(s))
