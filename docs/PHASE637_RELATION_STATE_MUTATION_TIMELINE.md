# Phase 637 — relation-state mutation timeline correlation

Phase 635 records a shared monotonic `runtime_event_sequence` across relation
mutation and solver observations. Phase 636 classifies all five static
`FUN_00757d20` caller sites. Phase 637 joins those two evidence surfaces
offline without assigning native scheduler semantics.

## Inputs

The analyzer consumes an existing full-mode `sdf-probe` capture directory.

Mutation stream:

- `relation_state_mutation_events.jsonl`

Timeline anchors:

- `frame_entry_*.json`;
- `pre_solve_*.json`;
- `provider_pre_*_*.json`;
- `provider_post_*_*.json`;
- `scalar_reset_events.jsonl`;
- `post_solve_*.json`.

Provider snapshots keep `runtime_event_sequence` in their metadata payload;
the correlator normalizes that representation with the top-level sequence used
by the other probe artifacts.

## Output

`analyze_relation_state_mutation_capture_directory(...)` emits:

`SHIFT.ConstraintRelationStateMutationTimelineCorrelation/1`.

Each mutation row preserves its source slot/branch/caller identity and adds:

- the nearest preceding captured timeline anchor;
- the nearest following captured timeline anchor;
- an exact `anchor_window`;
- the frame-entry consistency result;
- a conservative timeline position.

The only special pre-frame classification is:

`before-first-frame-entry`

and it is emitted only when a mutation has no captured frame index and its
sequence is strictly earlier than the first observed frame-entry sequence.

A mutation carrying a frame index is accepted only when:

1. that exact frame-entry artifact exists;
2. its `runtime_event_sequence` equals the mutation's captured
   `frame_entry_runtime_event_sequence`;
3. the mutation sequence is strictly later than that frame-entry sequence.

No higher-level gameplay event is inferred.

## Fail-closed checks

The report is blocked when any of the following occurs:

- the mutation JSONL stream is missing or empty;
- there are no runtime timeline anchors;
- an anchor lacks a positive sequence;
- runtime event sequences collide;
- a mutation slot is outside 0..3;
- Phase 636 call-site classification is not ready;
- a referenced frame-entry is missing;
- frame-entry sequence identity disagrees;
- a mutation is not later than its referenced frame-entry;
- a no-frame mutation appears after frame processing has already started;
- a mutation has no timeline neighbor at all.

Unexpected mutation events remain visible in the per-event report even when
they block top-level readiness.

## CLI

Run:

```bash
python tools/analyze_relation_state_mutation_timeline.py \
  /path/to/sdf-probe-capture \
  -o relation_state_mutation_timeline.json
```

Exit code is 0 only when the full correlation report is ready; blocked
evidence exits with 2.

## Evidence boundary

Phase 637 performs ordering correlation only. It does not:

- assign a fixed-step scheduler event;
- map `FUN_0079a050` to an unproven gameplay semantic;
- synthesize missing capture anchors;
- mutate CRRF or native vehicle state;
- authorize native relation mutation.

The report explicitly records:

- `runtime_event_sequence_only=true`;
- `native_scheduler_admission=false`;
- `semantic_event_inference=false`.

The next safe boundary is an authentic retail capture. Once a ready Phase 637
report exists for that capture, a separate native-admission phase can decide
which observed state belongs to construction/setup and which observed runtime
mutation can be represented without inventing timing.
