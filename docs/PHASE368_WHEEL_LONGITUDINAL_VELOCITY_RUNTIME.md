# Phase 368 — wheel longitudinal velocity runtime

Phase 368 reconstructs FUN_00755f80 and its immediate four-wheel caller
FUN_00763570.

## Exact single-wheel boundary

FUN_00755f80 reads the wheel physics body's pose at +0xD4 and shared velocity
at +0x48 through FUN_007af0a0. The returned local vector's X component is
retained as the wheel's longitudinal scalar.

The function then calls FUN_007af010 with that scalar and writes the resulting
three-component vector back by subtracting it from the same shared velocity:

velocity.x/y/z -= reconstructed.x/y/z

The transform helpers are intentionally externalized; their axis/matrix semantics
are not inferred here.

## Four-wheel orchestration

FUN_00763570 starts from this+0x400 and calls FUN_00755f80 for four objects at
0xA80-byte intervals. The four X components are stored in local_c0[0..3].

An additional branch replaces rear components 2 and 3 with their average when:

object+0x3EE0 is non-zero,
object+0x3EB8 is zero,
global configuration byte 0xC1286E is non-zero.

## Scope

This phase does not claim a tyre force law, wheel slip law, contact model, or
the meaning of the world-space subtraction beyond the observed state update.
