# Playable Linux slice — blocker swarm mode

Status: **RETIRED**

The blocker-swarm model existed only to keep three parallel workers productive. The project now has one active process, so swarm shards, semantic-owner routing, cross-process handoffs, and no-idle worker assignment are no longer active coordination mechanisms.

Canonical replacement:

[`PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md`](PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md)

Active machine-readable state:

[`../evidence/playable_slice_single_process_execution.json`](../evidence/playable_slice_single_process_execution.json)

The one process stays on the shortest blocker and may build only its immediate fail-closed consumer seam or blocker-specific reusable tooling when needed. It does not split the blocker across Process 1 / Process 2 / Process 3 shards.

Do not use `SHIFT.PlayableSliceBlockerSwarm/1` to select new work. Its evidence file is retained only as a retired historical coordination artifact.
