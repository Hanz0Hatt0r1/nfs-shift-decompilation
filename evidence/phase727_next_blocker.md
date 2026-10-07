# Phase 727 next blocker

Phase 727 proves and implements the final retail transform from `HDVehicle+0x3938` local query sample to the `FUN_007b0710` world position:

`BODY0.origin + BODY0.basis * local_sample`.

## NEXT_STEP

Two source-backed joins remain before this transform can replace the external world-position input in the active session:

1. Recover the producer of `HDVehicle+0x3938/+0x3940/+0x3948` inside `FUN_007618f0`. The retail writer span already proves it is a `FUN_00753590` vector addition between an unresolved local-base vector and a resource/config vector at the writer's `+0x918` source. Trace those inputs without inventing semantic names.
2. Expose the **current per-pass chassis BODY0 bytes** at the `FUN_00765c40` anchor. Pass 0 uses the incoming BODY state; pass 1 must use the BODY state after the first `FUN_00765470` half-step. Do not bind both passes to the outer-step initial snapshot.

The collision provider beneath `FUN_007b0710` / `FUN_0074f560` remains a separate external blocker.

Preserve the Phase 726 query-input contract and all earlier `FUN_007682c0`, scheduler and renderer closures.
