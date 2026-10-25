#!/usr/bin/env bash
# usage: pipeline.sh <board.kicad_pcb> <logdir>
set -u
B=$1; L=$2; shift 2
BL=/home/mark/Documents/abx-motion/.claude/handoff/bl; P=~/.cache/mark-mods/kicad-mcp-big-venv/bin/python
S="systemd-run --user --scope -q -p MemoryMax=6G -p MemorySwapMax=0"
mkdir -p $L
run() { n=$1; shift; $S $P "$@" > $L/$n.log 2>&1; rc=$?; echo "$n rc=$rc: $(grep -v property.h $L/$n.log | grep -E 'newplace:|buckplace:|routed|PWR_ zones|zones filled|Traceback|Error|PROBLEM|CONFLICT|overlap|mismatch|OUTSIDE' | tail -4 | tr '\n' ' ')"; [ $rc -eq 0 ] || exit $rc; }
run newplace $BL/newplace.py $B "$@"
run buckplace $BL/buckplace.py $B
run critical $BL/critical.py $B
run pours $BL/pours.py $B
run fill $BL/fill.py $B
