After solve dispatch completes, `FUN_007b4110` consumes the solved scalar vector at PhysicsSystem `+0x40` and applies JOINT/HINGE/BAR responses back into runtime body state.# Phase 389 — Per-frame SDF solver lifecycle

The runtime boundary now continues from static constraint graph construction into the per-frame solver entry `FUN_007b3f40` and body projection stage `FUN_007b4110`.

## Frame entry

With no provider at physics-system `+0x48`, the builtin path clears the scalar matrix at `+0x3c` and the RHS vector at `+0x40`. With a provider present, the reset is delegated to provider vtable `+0x20`.

After reset, `FUN_007b3ed0` refreshes JOINT/HINGE/BAR sampled transforms. `FUN_007b4110` then consumes the current solved scalar values by sampled base index and accumulates their contribution into body storage through `FUN_007baa70` and `FUN_007baaf0`.

## Scalar projection

JOINT consumes three consecutive doubles from sampled `+0x30`; HINGE consumes two from `+0x94`; BAR consumes one from `+0x30`. JOINT and BAR build body-side vectors from sampled transform data and pass them to the positive/negative accumulator helpers. HINGE uses the two scalar values in a direct signed coefficient combination against sampled frame components.

The accumulator coordinates are preserved structurally rather than relabeled as force/torque units. This keeps the decompilation source-faithful while avoiding unsupported physical-unit claims.

## Final solve dispatch

After the body projection stage and builtin diagonal-reset calls, provider-present execution dispatches to provider vtable `+0x18`; provider-absent execution calls `FUN_007b0f20` with RHS `+0x4c`, matrix +0x3c and scalar node count `+0x34`.

## Remaining unknown

The unresolved pieces are the provider-specific `+0x20/+0x18` implementations and the physical interpretation of the body accumulator state. The builtin graph, scalar-domain matrix population, frame ordering and sparse solver boundary are now represented separately.
