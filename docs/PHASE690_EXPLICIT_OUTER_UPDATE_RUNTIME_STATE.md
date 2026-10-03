# Phase 690 — explicit persistent outer-update runtime state

Phase 689 composes the currently proven native outer-update anchors:

```text
FUN_00770e80
  -> FUN_0076d100 required anchors
  -> FUN_00765470 machine-backed half-step
  -> persistent BODY bytes
  -> FUN_007b8810
```

for exactly two half-steps. It deliberately does not prove that the native
`NativeRuntimeState::fixed_step()` cadence is the retail `FUN_00770e80` cadence.

Phase 690 therefore adds persistence at the runtime-state boundary without
silently scheduling the composed chain.

## New runtime state

`native_runtime/src/runtime_explicit_outer_update_state.hpp` defines:

```text
SHIFT.NativeExplicitOuterUpdateRuntimeState/1
```

The state owns the raw persistent BODY byte buffer and records explicit update
count plus the last Phase 689 provider cardinalities.

Initialization requires:

- a ready native physics workspace;
- non-zero workspace BODY count;
- exactly `BODY_count * 0x170` bytes.

Execution additionally requires:

- `participant_ready=true`;
- `participant_identity_join_proven=true`;
- runtime BODY count unchanged from initialization.

Only after those checks does the state call the existing Phase 689 composed
outer-update primitive. The returned final BODY byte buffer becomes the input to
the next explicit outer update.

## NativeRuntimeState integration

`NativeRuntimeState` now owns:

```text
ExplicitOuterUpdateRuntimeState outer_update
```

and exposes two explicit methods:

```text
initialize_explicit_outer_update_body_state(...)
execute_explicit_outer_update(...)
```

The existing `fixed_step()` body is not extended with the new path. This is a
required evidence boundary, not an implementation omission: the repository has
not yet proven that one native fixed-step corresponds to a retail
`FUN_00770e80` invocation, to a rendered frame, or to any other engine cadence.

The older provider-absent `BodyFeedbackScheduler` therefore remains an
independent opt-in fixed-step mechanism. Phase 690 does not run both chains in
parallel automatically.

## Provider policy

Phase 690 does not synthesize refresh work between passes or outer updates.
Every explicit call still receives the Phase 689 providers for:

- the Phase 684 `FUN_0076d100` required-anchor callbacks;
- each Phase 688 machine/solver half-step input;
- the required `FUN_007b8810` post-half-step callback.

Thus persistent BODY bytes are the only state automatically carried across
explicit outer-update calls. Solver/contact/machine inputs remain external until
their retail producers and refresh timing are proven.

## Regression

`shift_runtime_explicit_outer_update_runtime_state_check` uses the same
six-scalar/two-BODY JOINT/HINGE/BAR deterministic fixture as Phase 689.

It verifies:

1. `NativeRuntimeState::fixed_step()` does not execute the explicit outer-update
   state when the legacy BODY feedback scheduler is disabled;
2. the first explicit call reuses the complete Phase 689 chain and reaches the
   previously frozen BODY-0 origin `(3.125, 4.65625, 6.1875)`;
3. the second explicit call receives the exact final BODY bytes of the first
   explicit call;
4. persistent BODY state continues changing across explicit calls;
5. workspace, participant-instance and participant-identity failures are
   rejected before any Phase 689 provider is invoked;
6. malformed initial BODY byte cardinality is rejected.

A matching Python scheduling oracle lives in:

```text
src/physics/explicit_outer_update_runtime_state.py
```

It freezes the admission and persistence policy independently of the native
physics arithmetic.

## Evidence boundary

Phase 690 proves a usable explicit runtime-state handoff for the already-proven
Phase 689 chain. It does **not** prove:

- automatic scheduling from `NativeRuntimeState::fixed_step()`;
- rendered-frame or engine-loop cadence;
- input/control intent propagation into retail wheel/drivetrain state;
- automatic per-pass solver/contact refresh;
- complete `FUN_0076d100`, `FUN_00765470` or `FUN_00770e80` semantics;
- the retail machine scalar path inside `FUN_007afdd0`.

The basis-rotation callback therefore remains explicit. Closing the targeted
machine/x87 scalar production of `FUN_007afdd0`, or independently proving the
outer-update cadence owner, are the next safe frontiers.
