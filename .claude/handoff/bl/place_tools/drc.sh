#!/usr/bin/env bash
# usage: drc.sh <board> <out.json>  -> summary vs drc_before.json
W=/tmp/claude-1000/-home-mark-Documents-VE-V3/412ee8fb-27c0-4acd-98aa-e7fcd601bdf3/scratchpad/place
rm -f $2; systemd-run --user --scope -q -p MemoryMax=6G -p MemorySwapMax=0 kicad-cli pcb drc --schematic-parity --severity-all --format json -o $2 $1 >/dev/null 2>&1
python3 - $2 <<'PY'
import json,collections,sys
W='/tmp/claude-1000/-home-mark-Documents-VE-V3/412ee8fb-27c0-4acd-98aa-e7fcd601bdf3/scratchpad/place'
for f in [W+'/drc_before.json', sys.argv[1]]:
    d=json.load(open(f)); print(f.rsplit('/',1)[1], dict(sorted(collections.Counter(v['type'] for v in d['violations']).items())), 'unconnected',len(d['unconnected_items']),'parity',len(d['schematic_parity']))
def S(f,t):
    d=json.load(open(f)); return {' | '.join(i['description'][:80] for i in v['items']) for v in d['violations'] if v['type']==t}
for t in ('starved_thermal','hole_to_hole','clearance','shorting_items','courtyards_overlap','silk_edge_clearance','track_dangling','via_dangling','hole_clearance'):
    new=S(sys.argv[1],t)-S(W+'/drc_before.json',t); gone=S(W+'/drc_before.json',t)-S(sys.argv[1],t)
    if new or gone: print(t,'NEW:',sorted(new),'GONE:',sorted(gone))
PY
