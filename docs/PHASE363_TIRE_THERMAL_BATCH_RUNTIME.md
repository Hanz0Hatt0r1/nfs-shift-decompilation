# Phase 363 — four-wheel tyre thermal runtime orchestration

Phase 363 reconstructs the call topology around the already recovered
FUN_00760b50 tyre thermal update.

## Boundary

The recovered FUN_00770e80 path invokes FUN_00760b50 once for each wheel after
the main physics passes. The wheel runtime object stride is 0xA80.

Observed wheel order:

FRONTLEFT -> FRONTRIGHT -> REARLEFT -> REARRIGHT

The new adapter delegates all arithmetic to SHIFT.TireThermalRuntime/1.

## Scope

This is orchestration, not a new tyre model. It does not infer tyre-force/contact
equations, share thermal state between wheels, assign physical units, or alter
the recovered reserve/failure branches.

Missing or extra wheel records are rejected rather than silently synthesized.

## Verification

Added SHIFT.TireThermalBatchRuntime/1 plus four-wheel ordering, cardinality,
and state-isolation tests. Renderer code and RENDER.bff remain untouched.
