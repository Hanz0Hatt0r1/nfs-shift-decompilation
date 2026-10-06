# S5 scheduler accumulator retail-execution frontier

This checkpoint preserves the current static progress without treating merged analyzer infrastructure as a retail semantic proof.

## BLOCKER

`S5 retail outer-update scheduler/cadence ownership`.

The playable slice needs source-backed continuous persistent physics. Host loop frequency cannot satisfy this gate.

## INPUT

Current main consumed:

```text
c0741101b9ecdec944048714f3a892fd9db5c580
```

Positive inputs:

- `SHIFT.PhysicsManagerSchedulerEntryOwner/1`;
- `SHIFT.OuterUpdateCallsiteStatic/1`.

Merged blocker-specific infrastructure:

- PR #1350: `SHIFT.SchedulerAccumulatorProducerFrontier/1` analyzer + targeted runner;
- PR #1351: `SHIFT.SchedulerAccumulatorValueProvenance/1` analyzer + regressions.

Those two formats are **not yet published retail-result artifacts**. Their merged PRs add the machinery and synthetic/fail-closed validation; they do not contain an actual `SHIFT.GhidraFunctionInstructions/2` output generated from the retail analyzed Ghidra project.

## OUTPUT

Saved machine-readable frontier:

```text
evidence/retail_scheduler_accumulator_producer_frontier.json
SHIFT.SchedulerAccumulatorRetailExecutionFrontier/1
```

## What is actually proven/verified

The positive source/callgraph layer fixes:

```text
FUN_007155e9
    -> 0x00715602 FUN_00715380
         -> 0x00715434 FUN_00713050
```

ABI export:

```text
FUN_007155e9(LONG *param_1)                  __fastcall, ECX only
FUN_00715380(void *this, float param_1)      __thiscall, param_1 at Stack[0x4]:4
```

`SHIFT.OuterUpdateCallsiteStatic/1` independently proves that `FUN_00713050` reads:

```text
this +0x348   scheduler accumulator
manager+0x388 integer rate used to derive update count
```

It does not prove the `FUN_00715380` writer surface.

## Exact proof gap

The next shortest edge is execution of the already-merged targeted static runner against the retail analyzed Ghidra project for exactly:

```text
FUN_007155e9
FUN_00715380
FUN_00713050
```

Required first output:

```text
SHIFT.GhidraFunctionInstructions/2
```

Only from that actual retail slice may the merged analyzers establish, in order:

1. exact `FUN_00715380 this+0x348` writer surface;
2. exact `Stack[0x4]:4 -> STORE value` dependency;
3. exact producer of the argument passed at `0x00715602`.

Synthetic fixture success is analyzer validation, not retail semantic evidence.

## CONSUMER

The same S5 proof, followed by controller-dispatch/rate semantics and final `retail_cadence_admitted` admission.

## GATES_CHANGED

None.

```text
retail_cadence_admitted = false
```

## LIMITS

Current technical execution constraint in this chat:

- container/Python execution backend returns `ClientError`;
- uploaded `shift (1).zip` is 112,571,831 bytes, above the 104,857,600-byte Files materialization limit;
- `SHIFT_tail.zip` is also above that limit;
- `out.zip` materializes, but it is not the required analyzed Ghidra project.

This limitation does **not** justify runtime capture, host-cadence substitution, or semantic guessing.

Not proven:

- retail `FUN_00715380 +0x348` writer surface;
- retail param1-to-store dependency;
- exact value producer at `0x00715602`;
- time units;
- controller runtime dispatch to `cPhysicsManager +0x18`;
- rate-source semantics for `+0x388`;
- rendered-frame equivalence.

## TESTS

`tests/test_retail_scheduler_accumulator_producer_frontier.py` locks this distinction: merged analyzer formats must remain classified as infrastructure until an actual retail machine result is published.

## NEXT_STEP

Execute `tools/ghidra/run_s5_scheduler_accumulator_slice.sh` against the already analyzed retail `SHIFT.exe` Ghidra project when an execution path is available. As soon as the first retail stage is independently positive, publish that versioned machine-readable result immediately before continuing upstream value provenance.
