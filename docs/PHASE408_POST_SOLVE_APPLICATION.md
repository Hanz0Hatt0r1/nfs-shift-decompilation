# Phase 408 — exact post-solve body application

`FUN_007b4110` consumes solved scalar values from the global solver vector at PhysicsSystem `+0x40` after the provider/builtin solve dispatch.

For JOINT records (stride `0xa0`, scalar base `+0x30`) the function reads three solved scalars and sends the result vector to `FUN_007baa70` on the positive body using sample `+0x7c +0x18`, and to `FUN_007baaf0` on the negative body using `+0x84 +0x18`.

For HINGE records (stride `0xa0`, scalar base `+0x94`) it does not touch the linear accumulators. Instead it adds `solved[0]*angular_row + solved[1]*linear_row` to positive angular channels `+0x48/+0x50/+0x58` and subtracts the same combination from the negative body.

For BAR records (stride `0xb8`, scalar base `+0x30`) it multiplies the solved scalar by the sampled direction `+0x40/+0x48/+0x50`, then applies that vector through `FUN_007baa70/baaf0` at positive/negative sample points.

The new runtime module executes these three paths using the already reconstructed body accumulator primitive, preserving exact component ordering and signs. No force/torque unit labels are introduced.
