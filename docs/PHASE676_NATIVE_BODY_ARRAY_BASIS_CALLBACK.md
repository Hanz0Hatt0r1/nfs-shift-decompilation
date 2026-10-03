# Phase 676 — native BODY-array basis callback scheduling

Phase 676 closes a narrow native integration gap between the already ported
`FUN_007bab70` arithmetic core and the source/machine-code-backed `FUN_007b2270`
BODY-array loop.  It does **not** invent the still-unported arithmetic of
`FUN_007afdd0`.

## Evidence boundary

The existing `SHIFT.BodyFrameIntegrationStatic/1` contract proves:

- `FUN_007b2270` iterates the BODY array in ascending storage order;
- BODY count is read from owner `+0x10`;
- BODY array pointer is read from owner `+0x14`;
- retail BODY stride is `0x170` bytes;
- each BODY receives the same f64 timestep;
- each element is passed to `FUN_007bab70` before the loop advances;
- inside `FUN_007bab70`, `FUN_007afdd0(BODY+0xd4, cross_vector*dt)` occurs
  between the already ported pre-basis and post-basis arithmetic.

Phase 674 exposed `execute_fun_007b2270_body_array_with_external_bases()`.  That
was intentionally conservative, but it allowed a caller to precompute all
post-`FUN_007afdd0` bases before the BODY loop.  Such precomputation is not the
retail operation order and becomes unsafe once the real basis writer is wired.

## Native contract

`shift_body_frame_integration.hpp` now exposes:

```text
BodyBasisRotationCallback
execute_fun_007b2270_body_array_with_basis_callback(...)
```

For each BODY, and only for that BODY, the native chain is:

```text
advance_fun_007bab70_pre_basis
  -> external basis provider for FUN_007afdd0
  -> complete_fun_007bab70_post_basis
  -> next BODY
```

The provider receives only the proven inputs:

```text
current 3x3 f32 basis
cross_vector * f64 timestep
```

It must return the resulting 3x3 f32 basis.  Phase 676 does not assign a
replacement implementation to that provider.

## Fail-closed behavior

The new path rejects or propagates failure for:

- a missing basis provider;
- NaN/Inf in the BODY state before provider invocation;
- NaN/Inf in the rotation increment;
- NaN/Inf returned in the updated basis;
- NaN/Inf timestep through the existing Phase 674 validation.

A non-finite BODY input is rejected before the provider is called, so invalid
state cannot leak into an external `FUN_007afdd0` implementation.

An empty BODY array is valid and does not invoke the provider.

## Reference oracle and regressions

`src/physics/body_array_basis_callback_runtime.py` is the Python scheduling
oracle.  It freezes only the newly introduced boundary:

- `0x170` BODY stride identity;
- ascending per-BODY provider invocation order;
- exactly one provider result per BODY;
- finite 3x3 provider result validation;
- no basis-rotation arithmetic claim.

Coverage:

- `tests/test_body_array_basis_callback_runtime.py`;
- `native_runtime/tests/body_array_basis_callback_check.cpp`;
- CTest target `shift_runtime_body_array_basis_callback`;
- dedicated GitHub Actions workflow `native-physics-phase676`.

The native regression uses distinct rotation increments for three BODY records
and verifies callback order `0.25, 0.50, 0.75`, plus missing-provider,
non-finite-input, non-finite-output, and empty-array cases.

## What this phase proves

Phase 676 proves a source-backed native scheduling boundary for the BODY array:
`FUN_007afdd0` can no longer be wired outside the per-element
`FUN_007bab70` ordering without bypassing the typed API added here.

This is an integration primitive toward persistent vehicle-state evolution.  It
is **not** proof of rendered-frame scheduler parity, vehicle ownership, or input
ownership.

## Remaining boundary

The next native step remains evidence-gated:

1. port exact `FUN_007afdd0` float/x87 precision and matrix multiplication order
   when its instruction/source arithmetic is sufficiently frozen; or
2. compose the already proven `FUN_00765470` solve -> post-solve ->
   `FUN_007b2270` anchor order without filling unresolved helper work with
   guessed behavior.

Until one of those boundaries is complete, the basis provider stays mandatory
and external.
