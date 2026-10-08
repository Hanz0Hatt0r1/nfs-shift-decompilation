# Process 2 P2.4 — native `FUN_00765c40` residual-pass frontier

P2.4 consumes the completed Process 1 P1.2 handoff for `FUN_00765c40`. The handoff authorizes removal of the top-level `FUN_00765c40` provider only after Process 2 preserves the complete retail pass and its proven side effects.

This change introduces the first blocker-based native contract after the historical Phase 753 CI-workflow freeze. It does **not** introduce a new phase-numbered workflow.

## Exact lower boundary

The lower collision implementation remains external by proof and by design:

- provider object pointer: global `0x00c133ac`;
- indirect dispatch: provider vtable slot `+0x1c0`;
- returned surface-record stride: `0x58`;
- physical/PhysX class identity is not promoted;
- replacing it with a guessed track-height or scene-query implementation is forbidden.

The native contract therefore represents this seam explicitly as `Fun00765c40SceneQueryBoundary`.

## Retail residual-pass order

The recovered PC-retail body establishes the following top-level order:

1. refresh the four-wheel pre-query plane/state lanes;
2. transform the selected vehicle query position;
3. execute `FUN_007b0710`, retaining the lower `0x00c133ac/+0x1c0` query seam;
4. commit `+0x38dc` cache state and `+0x38e0` collision scalar;
5. execute four `FUN_00752fa0` wheel state writes;
6. execute the registered wheel-job queue, which refreshes the four `+0x738` load terms;
7. execute `FUN_007584f0` persistent mutations;
8. write `+0x407c` as the count of strictly-positive wheel load terms;
9. refresh the four wheel pair-state lanes;
10. run the twelve-entry contact sweep and its conditional BODY accumulation;
11. if enabled, run the final optional four-entry BODY accumulator sweep.

`shift_fun_00765c40_residual_pass_contract.hpp` pins this order as an operational enum. The naming deliberately avoids assigning physical semantics to fields whose meanings Process 1 did not prove.

## State surfaces pinned now

The native contract also pins the machine-backed direct state geometry: four `+0x0a70`-family lanes, eight `+0x0ba0/+0x0ba8`-family lanes, twelve contact pointers at `+0x35c8`, twelve contact scalars at `+0x35f8`, the `+0x3660` flag, `+0x3668/+0x3670/+0x3678` peak state, `+0x407c` count, and the three persistent destinations of `FUN_007584f0` (`+0x0d40/+0x17c0/+0x3420`).

Two exact operations are already executable natively in this layer:

- `FUN_00752fa0`: wheel `+0x9f8 = index` and `+0xa00 = HDVehicle+0x98` source bits;
- `+0x407c`: count of the four `+0x738` load terms that compare strictly greater than zero.

## Fail-closed removal gate

This is not yet the provider-removal commit. The existing `NativeVehicleExternalProviderBundle.fun_00765c40` callback remains present and the external-provider count remains seven. Remaining computational stages must be implemented against native persistent state before the callback is deleted. The collision scene-query implementation itself remains external even after that deletion.
