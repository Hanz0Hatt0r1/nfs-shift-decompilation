# S5 scheduler caller-value producer frontier

This checkpoint preserves the current Process 1 progress on the playable-slice S5 blocker without promoting incomplete cadence semantics.

## BLOCKER

`S5 retail outer-update scheduler/cadence ownership`.

Current `main` now includes merged PR #1351, which proves the local machine-value dependency:

```text
FUN_00715380 explicit float param_1 (Stack[0x4]:4)
    -> unique this+0x348 STORE value dependency
```

Therefore this checkpoint no longer treats the local accumulator write as open. The shortest remaining value-provenance edge is upstream at `FUN_007155e9`.

## INPUT

Current `main` consumed by this revision:

```text
c0741101b9ecdec944048714f3a892fd9db5c580
```

Positive upstream contracts:

- `SHIFT.PhysicsManagerSchedulerEntryOwner/1`;
- `SHIFT.SchedulerAccumulatorProducerFrontier/1`;
- `SHIFT.SchedulerAccumulatorValueProvenance/1`.

Additional static exports:

- `functions.jsonl`;
- `callgraph.jsonl`;
- `evidence/outer_update_callsite_static.md`.

## OUTPUT

Machine-readable saved frontier:

```text
evidence/retail_scheduler_accumulator_producer_frontier.json
SHIFT.SchedulerAccumulatorCallerValueProducerFrontier/1
```

This is a **frontier**, not a positive retail-cadence handoff.

## Current proven/verified graph

```text
cPhysicsManager scheduler entry
    -> ...
    -> FUN_00713050
         reads this+0x348
         reads manager+0x388 rate

FUN_007155e9
    -> 0x00715602 FUN_00715380(this, float param_1)
                        |
                        v
                 this+0x348 STORE
```

PR #1351 proves only the lower local dependency `param_1 -> this+0x348`. It explicitly leaves the caller-side producer semantics open.

The exported ABI for `FUN_007155e9` has only its ECX parameter and no explicit float stack parameter. Therefore the float supplied at `0x00715602` must be established from instructions/state inside `FUN_007155e9`; the exact producer remains to be proven.

## CONSUMER

Remaining S5 cadence proof.

Shortest next static proof:

```text
FUN_007155e9
  exact argument feeding call 0x00715602
      <- backward value producer
```

The existing targeted scheduler instruction slice already contains `FUN_007155e9`, `FUN_00715380`, and `FUN_00713050`; no broad export is required.

## GATES_CHANGED

None.

```text
retail_cadence_admitted = false
```

must remain false.

## LIMITS

Still not proven:

- exact producer identity of the float argument at `0x00715602`;
- physical time units/meaning of that value;
- controller runtime indirect dispatch to `cPhysicsManager` vtable slot `+0x18`;
- retail rate-source semantics for manager `+0x388`;
- one invocation per rendered frame;
- host `1/60` equivalence.

Do not reopen the closed BODY integration writer path below `FUN_00770e80`.

## TESTS

`tests/test_retail_scheduler_accumulator_producer_frontier.py` regression-locks the fail-closed state and verifies that the already-closed local `param_1 -> +0x348` edge is no longer listed as a blocker.

## NEXT_OWNER

Current sequential critical-path process / Process 1 compatibility owner.

Next action: backward-slice the exact value fed to `FUN_00715380` at `0x00715602` inside `FUN_007155e9`. If that producer becomes independently positive, publish a versioned handoff immediately before continuing controller/rate semantics.
