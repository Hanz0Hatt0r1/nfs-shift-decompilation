# Phase 725 — exact residual FUN_00765c40 external-pass boundary

## Result

Phase 725 removes a misleading name from the active selected-session provider API without claiming unsupported collision semantics.

The top-level provider previously called `NativeVehicleContactFactorProvider` did not represent only `FUN_00758ad0` contact-factor arithmetic. That arithmetic already has a native implementation. The callback actually stood in for the still-external complete `FUN_00765c40` pass, whose downstream proven output is the four wheel `+0x738` load terms consumed later in the same `FUN_0076d100` pass.

The active session boundary is now:

- `NativeVehicleFun00765c40Provider`;
- bundle field `fun_00765c40`;
- result `Fun00765c40ExternalPassResult`;
- currently proven result field `load_terms` (`Fun00765c40LoadTerms`).

The lower historical `Fun0076d100MotionReadMachineInputProviderCallbacks.contact_factor` callback is retained only as an internal compatibility anchor. It is not the session-level semantic name.

## Preserved native work

Phase 725 does not move previously recovered logic back outside. Existing native work remains native, including the `FUN_00758ad0` contact-factor arithmetic, the `FUN_007b0710` collision-query record contract, and the wheel query/response join.

## Remaining external work

The complete `FUN_00765c40` pass remains external because the exact upstream wheel world-position producer, collision-provider behavior, and any other source-visible side effects have not yet been joined sufficiently to claim faithful internalization.

The active S6 provider count therefore remains seven. Phase 725 narrows and names the boundary; it does not decrement the count.

## Next proof target

Recover the exact `FUN_00765c40` wheel world-position producer and collision-provider joins. Only after those semantics are source-backed should the complete anchor be split further or internalized.
