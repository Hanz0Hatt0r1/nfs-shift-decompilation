# Phase 674 — native BODY frame integration core

Phase 674 ports the newly proven persistent BODY writer path from
`SHIFT.BodyFrameIntegrationStatic/1` into `shift_runtime_physics` without
inventing the still-unported internal arithmetic of `FUN_007afdd0`.

## Source-backed retail order

The static evidence proves that `FUN_007bab70` executes the persistent BODY
updates in this order:

1. `origin += motion_triplet * dt`;
2. `motion_triplet += accumulator_b * BODY[+0x90] * dt`;
3. form `rotation_increment = cross_vector * dt` and pass it to
   `FUN_007afdd0(BODY+0xd4, rotation_increment)`;
4. `prepared_vector += accumulator_a * dt`;
5. rebuild the symmetric tensor with `FUN_007ba630` using the updated basis;
6. compute `cross_vector = tensor * prepared_vector` through the exact native
   `FUN_007aefb0` transform boundary.

The native state keeps the proven storage lanes explicit:

- origin: `+0x00/+0x08/+0x10`;
- cross vector: `+0x18/+0x20/+0x28`;
- prepared vector: `+0x30/+0x38/+0x40`;
- accumulator A: `+0x48/+0x50/+0x58`;
- accumulator B: `+0x60/+0x68/+0x70`;
- motion triplet: `+0x78/+0x80/+0x88`;
- multiplicative scalar: `+0x90`;
- symmetric tensor: `+0xb0..+0xd0`;
- basis: `+0xd4..+0xf4`;
- reciprocal coefficients consumed by `FUN_007ba630`: `+0x138/+0x140/+0x148`.

No stronger physical unit/name is assigned to `+0x90` or to the opaque vector
lanes beyond the already proven structural roles.

## Why the API is split around the basis writer

The Process A evidence proves the call and high-level role of `FUN_007afdd0`,
but the current native evidence layer does not yet freeze all of its intermediate
float/x87 boundaries and matrix multiplication ordering. Replacing it with a
standard Rodrigues implementation would therefore be a guess.

`shift_body_frame_integration.hpp` consequently exposes two exact stages:

- `advance_fun_007bab70_pre_basis()` executes the origin/motion writes and
  produces the exact `cross_vector * dt` rotation input;
- `complete_fun_007bab70_post_basis()` accepts the basis after the retail
  `FUN_007afdd0` boundary, then executes the proven prepared-vector, tensor and
  cross-vector stages.

`execute_fun_007bab70_with_external_basis()` is a convenience composition of
those stages. The external-basis parameter is an explicit evidence boundary,
not a synthesized orientation result.

## BODY array loop

`execute_fun_007b2270_body_array_with_external_bases()` ports the proven
`FUN_007b2270` orchestration shape: one common timestep is applied to each BODY
in array order. The retail owner offsets (`count +0x10`, array pointer +0x14,
stride `0x170`) remain ABI evidence rather than being recreated as raw byte
pointer arithmetic in the typed native API.

## Reused native primitives

The post-basis stage reuses the already admitted exact helpers:

- Phase 655 `build_fun_007ba630_body_tensor()`;
- `transform_fun_007aefb0_refresh()` for the source-backed f32-matrix/f64-vector
  boundary.

This avoids creating a second implementation of the same tensor/transform
arithmetic.

## Regression

`shift_runtime_body_frame_integration_check` verifies:

- origin uses the incoming motion triplet before the motion update;
- accumulator-B/scalar/timestep motion update;
- rotation increment construction;
- pre-basis stage does not prematurely update prepared-vector or basis;
- accumulator-A prepared-vector update after the basis boundary;
- tensor rebuild plus tensor-vector cross-vector refresh;
- two-element `FUN_007b2270` array ordering;
- BODY/basis array cardinality rejection;
- non-finite fail-closed handling.

`native-physics-recent` is extended through Phase 674.

## Remaining join

Phase 674 deliberately does **not** schedule the new integrator in
`NativeRuntimeState`. The next required proof/port is the exact internal
`FUN_007afdd0` basis rotation, including its retail precision/order boundaries.
Once that helper is native, the now-proven Process A schedule can connect:

```text
physics pass
  -> solve/post-solve feedback
  -> FUN_007b2270 / FUN_007bab70 persistent BODY update
  -> next half-step
```

The static evidence already proves two `0.5 * outer_dt` half-step invocations
inside `FUN_00770e80`; renderer-frame frequency and higher-level input ownership
remain separate boundaries.
