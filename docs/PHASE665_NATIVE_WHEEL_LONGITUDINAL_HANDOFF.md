# Phase 665 — native wheel longitudinal scalar/vector handoff

Phase 665 ports the source-backed arithmetic boundary recovered in Phase 368 for `FUN_00755f80` and its immediate four-wheel caller `FUN_00763570`.

This is intentionally not a full transform port. The current repository evidence freezes the caller-visible handoff around `FUN_007af0a0` and `FUN_007af010`, but it does not yet freeze the implementation/axis convention of `FUN_007af010`. The native boundary therefore accepts the already-produced local and reconstructed vectors instead of inventing that transform.

## Source-backed boundary

Phase 368 establishes the single-wheel sequence:

1. `FUN_007af0a0(body + 0xd4, body + 0x48, local_vec3)`;
2. retain `local_vec3.x` as the source-visible longitudinal scalar;
3. call `FUN_007af010` with that scalar to produce a three-component reconstructed vector;
4. update the shared velocity triplet in source order as `velocity.x/y/z -= reconstructed.x/y/z`.

It also establishes the caller layout:

- first wheel object: `this + 0x400`;
- stride: `0xA80`;
- count: four;
- reported components correspond to wheel indices `0..3`;
- rear components 2 and 3 are replaced by `(component[2] + component[3]) * 0.5` only when `object+0x3EE0 != 0`, `object+0x3EB8 == 0`, and global configuration byte `0xC1286E != 0`.

The Python/reference oracle remains `src/physics/wheel_longitudinal_velocity_runtime.py`, backed by `evidence/wheel_longitudinal_velocity_evidence.json`.

## Native API

`shift_wheel_longitudinal_velocity.hpp` exposes two deliberately precomputed boundaries:

- `execute_fun_00755f80_precomputed_handoff()` preserves the exact X-component extraction, object-offset mapping, and component-wise subtraction after the two external transforms have produced their vectors;
- `execute_fun_00763570_precomputed_batch()` preserves the four-wheel index mapping and the proven three-condition rear-pair averaging branch.

`apply_fun_00755f80_reconstructed_subtraction()` is kept separately testable so the persistent-state mutation arithmetic is not conflated with transform production or runtime scheduling.

All source-visible vectors and arithmetic in this handoff use `double`. No physical units or tyre/slip semantics are assigned to the scalar or subtraction.

## Fail-closed behavior

The native boundary rejects:

- wheel indices outside `0..3`;
- duplicate/missing wheel indices in the four-wheel batch;
- non-finite vector/scalar input;
- non-finite subtraction results;
- non-finite rear-pair averaging results.

This validation is a native safety contract. It does not claim that retail performed the same exception-based checks.

## Regression and CI

`shift_runtime_wheel_longitudinal_velocity_check` covers:

- exact layout constants (`0x400`, `0xA80`, four wheels, `+0x48`, `+0xD4`);
- single-wheel X-component extraction;
- source-order three-component subtraction;
- deterministic wheel-index reordering into `0..3`;
- the exact rear-pair average and both documented gate blockers;
- malformed wheel indices, duplicate indices, non-finite input, and overflow to non-finite output.

The target is registered through `native_runtime/cmake/recent_physics.cmake`, and `native-physics-recent` now covers Phases 656–665.

## Evidence gates intentionally left open

Phase 665 does not implement `FUN_007af010`, does not infer its matrix/axis semantics, and does not schedule `FUN_00755f80`/`FUN_00763570` in `NativeRuntimeState`.

For the higher-priority `FUN_007675f0` chain, the primary `FUN_007551e0` response application still requires exact source-visible post-transform arguments, and the two `FUN_007ba9e0` submissions still require exact world-point/contribution vectors before either join can be ported safely.
