# Phase 669 — native spring gap/history state primitive

Phase 669 ports the source- and machine-code-backed state transition in `FUN_007555b0`, called by `FUN_00755950` from the `FUN_00758b50` wheel-kinematics path.

The reference oracle is `src/physics/spring_helper_runtime.py`, backed by `evidence/spring_helper_runtime_evidence.json`. This phase deliberately stops before the caller-side x87 return consumed by `FUN_00755950`, because the recovered callee prototype does not establish stable semantics for that value.

## Proven boundary

The recovered state layout is:

- lower boundary: helper `+0x238`;
- upper boundary: helper `+0x240`;
- current gap: helper `+0x248`;
- previous gap: helper `+0x250`;
- transition trigger value: helper `+0x258`;
- crossing flag: helper `+0x260`.

The exact source-visible arithmetic is preserved in order:

```text
if displacement <= upper_boundary:
    current_gap = upper_boundary - displacement
else:
    current_gap = displacement - lower_boundary

transition = current_gap > 0 && previous_gap < 0
```

On the proven transition, the passed trigger value is associated with the `+0x258` write. No physical units or spring-force semantics are assigned to any scalar.

## Native API

`shift_spring_gap_state.hpp` exposes:

- `compute_fun_007555b0_gap()` for the exact two-branch scalar expression;
- `execute_fun_007555b0_gap_state()` for the proven previous/current-gap crossing test and conditional trigger-value handoff.

The native representation uses `double`, matching the existing Phase 365 reference oracle and the recovered QWORD/x87 state/caller boundary. Arithmetic is not widened beyond that API boundary.

## Fail-closed behavior

The native primitive rejects:

- negative spring type values;
- non-finite displacement, boundaries, previous gap, or trigger value;
- arithmetic that overflows to a non-finite current gap.

These checks are native safety behavior, not a claim that retail used exceptions or equivalent validation.

## Regression and CI

`shift_runtime_spring_gap_state_check` covers:

- all recovered state/boundary offsets;
- both arithmetic branches and the `<=` equality boundary;
- positive-current/negative-previous crossing behavior;
- no transition when previous gap is non-negative;
- no transition when current gap is exactly zero;
- rejection of negative spring type, non-finite state, and non-finite arithmetic results.

The target is registered through `native_runtime/cmake/recent_physics.cmake` and included in `native-physics-recent`.

## Explicitly unresolved

Phase 669 does **not** implement or name the x87 value consumed by:

```text
FUN_00755950 -> FUN_007555b0 -> FSTP QWORD PTR [runtime+0x548]
```

It also does not schedule `FUN_00755950`, `FUN_00758b50`, or `FUN_0076d100`, and it does not connect this state primitive to a guessed tyre/suspension force law. Those remain separate evidence gates.
