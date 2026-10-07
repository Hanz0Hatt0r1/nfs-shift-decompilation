# Phase 727 — exact FUN_00765c40 local-sample to world-position transform

## Result

Phase 727 uses the exact retail PC `SHIFT.exe` machine code to recover the final position transform immediately before `FUN_00765c40` calls `FUN_007b0710`.

The retail path is two explicit machine helpers:

1. `FUN_007aefb0` multiplies the `HDVehicle+0x3938/+0x3940/+0x3948` local `f64 vec3` by the selected chassis BODY0 `3x3 f32` basis at `BODY0+0xd4..+0xf4` and stores an `f64 vec3` at `HDVehicle+0x38f0`.
2. `FUN_00753590` adds the BODY0 origin at `+0x00/+0x08/+0x10` to that rotated vector.

Therefore the query world position is exactly:

`BODY0.origin + BODY0.basis * HDVehicle.local_sample_0x3938`

This is the wheel-query transform used by retail code. It is not borrowed from the renderer BODY0/VHF chain.

## Native implementation

`execute_fun_00765c40_world_position_transform()` consumes one exact `BodyRecordBytes` chassis record and the local sample vector. It preserves the retail row grouping visible in `FUN_007aefb0`, stores each rotated component to `f64`, then performs the separate BODY0-origin addition matching `FUN_00753590`.

The BODY layout reuses the already-proven native BODY adapter offsets:

- origin: `+0x00/+0x08/+0x10`, `f64`;
- basis: `+0xd4..+0xf4`, nine contiguous `f32` values.

## New upstream boundary

The local sample itself is not guessed. Retail `FUN_007618f0` visibly writes it to `HDVehicle+0x3938/+0x3940/+0x3948`; the writer span uses `FUN_00753590` to add an unresolved local-base vector to a source/config vector at the writer's `+0x918` input.

Phase 727 therefore moves the blocker upstream from “unknown world position transform” to “recover the producer semantics of `HDVehicle+0x3938`”.

## Runtime join remains separate

The exact transform is native-ready, but the selected-session runtime does not yet call it. The remaining runtime-timing issue is to provide the **current per-pass chassis BODY0 snapshot** at the `FUN_00765c40` anchor: pass 1 must observe the BODY state after the first half-step, not an outer-step stale snapshot.

The active external-provider count remains seven.
