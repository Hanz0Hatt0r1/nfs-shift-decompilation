# Phase 647 — anchored stop after relation-state mutation

Phase 646 made long relation-timeline observation cheap enough to run under
Wine/GDB. The first authentic long-window capture then established a useful
negative result: a 600-post-solve-frame lightweight session produced 600 frame
entry anchors and 600 post-solve anchors, but no `FUN_00757d2c` relation-state
mutation.

The supplied evidence archive
`065c831a5dc720101662748bd43d78a08a057dbfaa485190eedb15747ab99ad3`
contains one capture session
`c6548ef72df04cc28b068678e185142b`, 1200 contiguous runtime-event sequence
numbers, one stable physics-system pointer and no missing or duplicate anchor
sequence. All 1201 files declared by the evidence manifest match their recorded
sizes and SHA-256 hashes.

That makes a fixed short runtime window the wrong capture strategy for the
remaining mutation evidence. The four known `FUN_0076ed60` callers are setup
calls and may occur before the normal frame loop, while the fifth
`FUN_0079a050` caller is conditional.

## New stop policy

The launcher and embedded GDB probe now accept:

```bash
--stop-after-relation-mutation
```

When enabled, `RelationStateMutationProbe` writes each complete event and
sets an observation latch without stopping the inferior. The first following
post-solve anchor writes its own timeline record and then returns a GDB stop.
The generated command file detaches and quits automatically.

The option can be combined with `--capture-frames N`. In that form the capture
ends on whichever happens first:

1. the first post-solve anchor after an authentic `FUN_00757d2c` mutation; or
2. the Nth post-solve anchor.

This makes a large frame budget a safe fallback rather than the primary
evidence trigger while preserving the mutation-to-next-anchor relationship.

## Intended capture

For the outstanding setup/runtime provenance question, use
`--relation-timeline-only --stop-after-relation-mutation` and arm the probe before
vehicle/race setup. A large `--capture-frames` value can be supplied as a
failsafe.

Provider-only mode rejects this option because that mode deliberately omits the
relation-state mutation breakpoint.

## Evidence boundary

Phase 647 changes debugger termination only. It does not synthesize a mutation,
reinterpret the 600-frame negative observation, infer gameplay semantics, or
authorize native fixed-step scheduling.
