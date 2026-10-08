# Process 2 P2.4 — `FUN_00765c40` wheel-pair refresh stage

## BLOCKER

P2.4 is internalizing the residual `FUN_00765c40` pass from the completed Process 1 ownership handoff. The top-level callback cannot be removed until every source-visible stage is preserved in retail order.

## INPUT

This slice consumes the already-merged contracts:

- `SHIFT.Fun00765c40ResidualPassContract/1`;
- `SHIFT.Fun00765c40DirectMachineWriteSurface/1`;
- PC-retail `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

The direct machine surface proves two qword stores per wheel at sites `0x0076606b` and `0x00766073`, with four wheel records at stride `0x0a80`.

## OUTPUT

Adds `SHIFT.Fun00765c40WheelPairRefreshStage/1`.

Native code now owns the exact eight destination lanes:

```text
+0x0ba0 / +0x0ba8
+0x1620 / +0x1628
+0x20a0 / +0x20a8
+0x2b20 / +0x2b28
```

The stage is pinned immediately after the `+0x407c` positive-load-count commit and immediately before the contact-array sweep.

The upstream arithmetic that produces these qwords is not yet sufficiently recovered for a native formula. Therefore the stage accepts the four source-computed qword pairs explicitly and preserves them bit-for-bit. No floating-point interpretation or physical field name is invented.

## GATES_CHANGED

- all eight wheel-pair destinations are native-owned;
- exact stage ordering is compile-time tested;
- source-computed pair values remain an explicit unresolved input;
- complete `FUN_00765c40` internalization remains false;
- `NativeVehicleExternalProviderBundle.fun_00765c40` remains present;
- external provider count remains 7.

## LIMITS

This slice does not reconstruct the preceding x87 arithmetic, does not infer units or semantic names for the qword pairs, and does not change the lower scene-query boundary.

## TESTS

`shift_runtime_fun_00765c40_wheel_pair_refresh_stage_check` pins destination geometry, stride, retail ordering, and bit-preserving materialization. `tests/test_p2_4_fun_00765c40_wheel_pair_refresh_stage.py` cross-checks the native header, evidence contract and provider-removal gate.

## NEXT_STEP

Internalize the 12-slot contact-array sweep and its bounded state updates while keeping unresolved computed values explicit. Remove the top-level `FUN_00765c40` callback only after the complete retail pass is executable natively.
