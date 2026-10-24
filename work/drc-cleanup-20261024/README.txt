Checkpoint-specific DRC cleanup audit aids. Baseline41f87bf.
Active deliverable is root abx-motion project; variant snapshot was not modified.

Accepted operations:
 copper_cleanup.py: graph nonbridge deletion plus native pad-group proof.
 trim_tails.py: trim loose ends to real junctions; add explicit center joins.
 thermal_and_silk.py: GND TIM pad and label/frame clearance.
 repair_tim_route.py: route control signal clear of exposed GND thermal pad.
 library_and_draft_metadata.py: reviewed library aliases, schematic links and
 actual board-only status for49 unwired reserves.
 branch_cleanup.py: follow native dangling branches, preserving pad groups.

Scripts are NOT idempotent. Do not rerun them over the completed cleanup.
The source data before editing is retained locally in before.*; the immutable
Git baseline and final validation/audit provide portable review evidence.
Intermediate trials/reports are superseded by validation/drc-cleanup-20261024.
No manufacturing release or completed Ethernet circuit is claimed.
