# Phase 659 — native auxiliary contact-response chain

Phase 659 closes the complete source-backed `FUN_00758fc0` arithmetic/application chain by composing primitives already reconstructed in Phases 656–658.

## Exact execution order

For one auxiliary record the native executor now performs:

1. `FUN_007aefb0(BODY + 0xd4, record + 0x68)` to obtain the transformed record point;
2. `FUN_007537b0(BODY, transformed_point)` using BODY `+0x18/+0x20/+0x28` and `+0x78/+0x80/+0x88`;
3. `FUN_007af0a0(BODY + 0xd4, body_point_output)`;
4. subtract the caller-supplied reference point;
5. require the record active flag and `relative.z < 0`;
6. evaluate `FUN_00755340(record + 0x48, relative.x, relative.z)`;
7. form the proven local response `(0, directional * gain * z^2, scale * z^2)`;
8. transform that response through `FUN_007aefb0(BODY + 0xd4, ...)`;
9. apply it with `FUN_007baa70(BODY, transformed_record_point, transformed_response)`.

Inactive records and records whose relative Z is non-negative leave the BODY accumulator unchanged.

## Native composition

The chain reuses, rather than duplicates:

- Phase 629 exact `FUN_007aefb0` / `FUN_007af0a0` float-matrix boundaries;
- Phase 658 `FUN_007537b0` BODY point transform;
- Phase 657 `FUN_00755340` directional response;
- Phase 656 `FUN_007baa70` BODY accumulator primitive.

The result remains semantically neutral. The record gain/scale/curve fields are not renamed to undocumented force or tyre quantities.

## Regression

`shift_runtime_aux_contact_response_check` proves:

- the complete active chain through BODY accumulator application;
- exact transformed point and relative-point intermediates for an identity frame fixture;
- the squared-negative-Z response;
- unchanged BODY state for an inactive record;
- unchanged BODY state for the non-negative-Z gate;
- fail-closed rejection of non-finite input.

## CI hardening

`.github/workflows/native-physics-recent.yml` now builds and executes the recent native physics regressions for Phases 656–659. This closes the previous gap where those targets were compiled by `linux-vulkan` but not explicitly selected by one of its named CTest steps.

## Remaining boundary

The two auxiliary record instances are known at `this + 0x37d8` and `this + 0x3858` with `0x80` stride, but Phase 659 does not schedule them inside `NativeRuntimeState`. Authentic per-fixed-step record/reference production and the still-unresolved BODY pose writer remain separate runtime-evidence gates.
