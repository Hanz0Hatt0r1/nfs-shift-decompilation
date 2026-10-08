# Phase 746 — primary `FUN_00766510` caller accumulator delta

Phase746 extends the already-native Phase742 primary response block by one immediately-following source-visible operation. It does **not** claim the whole `FUN_00766510` accumulator or callback is native.

## PC retail sequence

At PC decompiler lines 759686–759692, the primary block performs:

```text
FUN_007551e0(HDVehicle+0x3950, ...)
FUN_007aefb0(BODY0+0xd4, response, transformed_response)
FUN_007baa70(BODY0, HDVehicle+0x38f0, transformed_response)
FUN_00753650(cross_out, HDVehicle+0x38f0, transformed_response)
HDVehicle+0x40a0 += cross_out.x
HDVehicle+0x40a8 += cross_out.y
HDVehicle+0x40b0 += cross_out.z
```

The PC machine span `0x00766fc3..0x0076701e` is SHA-256 locked in the Phase746 evidence. The narrower cross/store span `0x00766fd6..0x0076701e` is also frozen separately.

## `FUN_00753650`

PC source line 749322 shows `FUN_00753650` as a plain three-lane cross product with argument order `(left, right)`:

```text
left.y * right.z - left.z * right.y
left.z * right.x - left.x * right.z
left.x * right.y - left.y * right.x
```

Phase746 exposes this existing operation as `execute_fun_00753650_cross_product()`. The existing `FUN_007baa70` native primitive now uses the same helper for its angular delta.

## Phase742 active contract extension

`SHIFT.Fun00766510PrimaryResponseApplication/2` keeps the Phase742 inputs and outputs, and adds:

```text
caller_accumulator_delta
```

This value is computed by an explicit call to the native `FUN_00753650` primitive using the same application point and transformed response. It is not reconstructed by subtracting BODY accumulator states, avoiding an unnecessary extra rounding path.

The historical Phase742 evidence remains `SHIFT.Fun00766510PrimaryResponseApplication/1`; Phase746 extends only the active runtime contract.

## Whole-function accumulator inventory

`FUN_00766510` begins by zeroing `HDVehicle+0x40a0/+0x40a8/+0x40b0`. Across the full function the state can receive:

- four direct `FUN_00753650` cross-product additions in the caller;
- up to two more cross-product additions inside the two `FUN_00758fc0` auxiliary calls;
- one final transformed-vector addition near function exit.

Phase746 closes only the direct site associated with the Phase742 `+0x38f0/+0x3950` primary response block. The other sites remain separate evidence/integration targets.

## Scope

The active external provider count remains **7**. `NativeVehicleContactResponseProvider` is not removed. Phase746 neither assigns physical meaning to `+0x40a0/+0x40a8/+0x40b0` nor claims the entire caller accumulator is native.
