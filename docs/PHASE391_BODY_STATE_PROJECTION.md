# Phase 391 — SDF body-state projection and coupling

`FUN_007bc680` is the next execution boundary after the per-body accumulator reset in Phase 390. It transforms the body residual state, projects it through JOINT/HINGE/BAR sampled constraints, and then applies same-type coupling passes before the frame solver dispatch.

## Residual transform

The source forms three residual values from body storage:

- x = `+0x48 - (+0x40*+0x20 - +0x38*+0x28)`
- y = `+0x50 - (+0x30*+0x28 - +0x40*+0x18)`
- z = `+0x58 - (+0x38*+0x18 - +0x30*+0x20)`

The triplet is transformed through `FUN_007aefb0` using the body frame at `+0xb0`. The linear state at `+0x60/+0x68/+0x70` is scaled by `+0x90` before entering the constraint helpers.

## Constraint projection order

The retail order is:

`FUN_007aefb0 -> FUN_007bac60 -> FUN_007bae40 -> FUN_007bb090 -> FUN_007bbb80 -> FUN_007bb250 -> FUN_007bb6c0`.

The first three constraint helpers handle JOINT, HINGE and BAR contributions against the primary accumulator at `+0x150`. `FUN_007bbb80` is a shared post-projection stage. The final two helpers apply HINGE-HINGE and BAR-BAR matrix coupling through the per-body row-pointer table at `+0x158`.

## Same-type coupling

`FUN_007bb250` walks HINGE samples and `FUN_007bb6c0` walks BAR samples. Both use the sample-side flag to determine the sign of the contribution: equal flags add the value; differing flags subtract it. The result is written into the solver matrix rows referenced by the global scalar base indices.

## Boundary

This phase intentionally preserves accumulator fields and matrix coefficients as source coordinates. No force/torque unit, inertia interpretation or provider-specific numerical meaning is inferred.
