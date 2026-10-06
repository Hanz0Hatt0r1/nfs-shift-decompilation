# S5 scheduler accumulator producer frontier

This checkpoint exists to preserve Process 1 progress on the current playable-slice blocker without promoting incomplete cadence semantics.

## BLOCKER

`S5 retail outer-update scheduler/cadence ownership`.

The already-published `SHIFT.PhysicsManagerSchedulerEntryOwner/1` proves the Physics Manager-owned scheduler-entry chain down to `FUN_00713050`. The remaining work is to prove the controller runtime dispatch and the producer semantics of the accumulator/rate inputs used by the batch scheduler.

## INPUT

Current `main` at checkpoint creation:

```text
e4dff67054770a4496fcf664b646180648e6becc
```

Static exports and committed contracts used:

- `functions.jsonl`;
- `callgraph.jsonl`;
- `evidence/outer_update_callsite_static.md`;
- `tools/ghidra/build_outer_update_callsite_contract.py`;
- `SHIFT.PhysicsManagerSchedulerEntryOwner/1`.

## OUTPUT

Machine-readable frontier:

```text
evidence/retail_scheduler_accumulator_producer_frontier.json
SHIFT.RetailSchedulerAccumulatorProducerFrontier/1
```

This is a **frontier**, not a positive retail-cadence handoff.

## Current verified narrowing

The exported ABI says:

```text
FUN_00715380(void * this, float param_1)     __thiscall
FUN_007155e9(LONG * param_1)                 __fastcall / ECX only
```

The static callgraph fixes:

```text
0x00715602  FUN_007155e9 -> FUN_00715380
```

Therefore the float argument consumed by `FUN_00715380` is established inside `FUN_007155e9` or loaded there from state; it is not an explicit float argument supplied to `FUN_007155e9` through its exported ABI.

Separately, the existing outer-update static contract verifies that `FUN_00713050` consumes:

```text
this + 0x348   source-visible scheduler accumulator
manager +0x388 integer rate used to derive the substep count
```

This does **not** yet prove that `FUN_00715380::param_1` is elapsed time, that it writes `this+0x348`, or that the controller invokes the Physics Manager scheduler exactly once per rendered frame.

## CONSUMER

The consumer is the remaining S5 cadence proof. It should consume this frontier plus the targeted `SHIFT.GhidraFunctionInstructions/2` slice for only:

```text
0x007155e9
0x00715380
```

and the already-merged BManager dispatch slice infrastructure from PR #1349.

## GATES_CHANGED

None.

```text
retail_cadence_admitted = false
```

must remain false at this stage.

## LIMITS

Do not promote any of the following without exact instruction/p-code provenance:

- `FUN_00715380::param_1 == elapsed frame time`;
- `param_1 -> this+0x348`;
- `this+0x348 == host dt`;
- one Physics Manager scheduler invocation per rendered frame;
- host `1/60` as retail cadence;
- BManager lifecycle adjacency as proof of Tick slot semantics.

Do not reopen the already-closed BODY integration writer path below `FUN_00770e80`.

## TESTS

`tests/test_retail_scheduler_accumulator_producer_frontier.py` regression-locks the fail-closed status and the exact remaining blockers.

## NEXT_OWNER

Current sequential critical-path process / Process 1 compatibility owner.

Next action: use the existing targeted Ghidra instruction/p-code runner on `FUN_007155e9` and `FUN_00715380`, then prove the stack value reaching `0x00715602` and the exact write/read-modify-write provenance of `this+0x348`.
