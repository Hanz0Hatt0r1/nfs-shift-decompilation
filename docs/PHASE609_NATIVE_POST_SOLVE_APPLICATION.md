# Phase 609 — native FUN_007b4110 post-solve application primitives

Phase 608 can execute an evidence-prepared provider-absent solver frame on each
native fixed step, but deliberately stops before applying the solved scalar
vector to body state.

The exact post-solve application itself was already recovered in Phases 392,
402 and 408. Phase 609 ports that source-backed numerical layer to native C++
without yet attaching it to the scheduler.

## Source functions

The native implementation preserves:

- `FUN_007b4110` — post-solve scalar-vector application;
- `FUN_007baa70` — positive body accumulator update;
- `FUN_007baaf0` — negative body accumulator update.

The body accumulator channels retain their recovered raw storage interpretation:

- angular: `+0x48/+0x50/+0x58`;
- linear: `+0x60/+0x68/+0x70`.

No force/torque units are assigned.

## Body accumulator primitive

For lever arm `p`, contribution vector `v`, and sign `s ∈ {-1,+1}`:

```text
linear_delta  = s * v
angular_delta = s * (p × v)
```

This is the native equivalent of `FUN_007baa70/baaf0`.

## JOINT

A JOINT consumes three solved scalars.

The 3-vector is applied:

- positively to the positive body through `FUN_007baa70`;
- negatively to the negative body through `FUN_007baaf0`.

Positive and negative lever arms remain independent inputs, matching the
recovered sample-side addresses.

## HINGE

A HINGE consumes two solved scalars.

For each body side:

```text
delta = solved[0] * angular_row + solved[1] * linear_row
```

The positive body adds the delta; the negative body subtracts its own sampled
row combination.

HINGE does not modify the linear accumulator in this post-solve path.

## BAR

A BAR consumes one solved scalar.

```text
vector_solution = bar_direction * solved_scalar
```

That vector is then passed through the positive/negative accumulator helpers.

## Native API

New native header:

`native_runtime/include/shift_post_solve_application.hpp`.

New implementation:

`native_runtime/src/post_solve_application.cpp`.

The API exposes neutral body accumulator state and exact JOINT/HINGE/BAR
application functions. It does not require or invent retail body pointers.

## Regression parity

`shift_runtime_post_solve_check` reproduces the existing Python Phase 408
fixtures:

- positive/negative cross-product accumulator deltas;
- JOINT 3-scalar application;
- HINGE 2-scalar angular-only application;
- BAR direction × scalar application;
- invalid sign rejection.

Linux Vulkan CI runs the CTest target and checks the executable report:

`SHIFT.NativePostSolveApplicationCheck/1`.

## Boundary after Phase 609

The post-solve arithmetic is now native and source-backed, but it is not yet
executed by the Phase 608 fixed-step scheduler.

That integration still requires an exact constraint/body projection packet
describing, for the same solver frame:

- JOINT/BAR positive and negative body targets;
- positive/negative lever arms;
- HINGE positive/negative sampled angular and linear rows;
- BAR directions;
- scalar bases and widths.

Until that body/sample mapping is supplied as explicit evidence, Phase 608
continues to report:

`physics_solver_post_solve_body_state_applied=false`.
