# Phase 663 — native FUN_00766510 response-input join

Phase 663 closes the source-backed producer of the `local_200` response-input vector consumed by `FUN_007551e0` inside `FUN_00766510`.

Phase 373 already established the exact retail sequence at source line 759553:

```text
FUN_007af0a0(body + 0xd4, body + 0x18, local_200)
FUN_007551e0(body + 0x3950, &local_60, local_200, local_1b8, &local_78)
```

The Phase 657 native port still accepted `response_input` as an external argument. Phase 663 removes that gap by composing the already-native exact `FUN_007af0a0` transform boundary with the existing native `FUN_007551e0` response builder.

## Native boundary

`transform_fun_00766510_response_input()` now consumes:

- the BODY frame at source offset `+0xd4`;
- the source vector at BODY offset `+0x18`;

and executes the established `transform_fun_007af0a0_refresh()` float-matrix boundary.

`evaluate_fun_00766510_contact_response_from_body_source()` then passes that transformed result through the existing `FUN_00766510` query/directional stage and `FUN_007551e0` quadratic response path.

The response result also records the exact transformed input used by the response builder so the join is externally auditable in regression output.

## Semantics intentionally not promoted

The source vector at BODY `+0x18` remains physically unnamed. Phase 373 explicitly did not prove that it is linear velocity, relative velocity, impulse, force, or any other physical quantity, and Phase 663 preserves that restriction.

Likewise this phase does not schedule the wheel-contact chain in `NativeRuntimeState` and does not identify or synthesize the unresolved vehicle pose writer.

## Regression

`shift_runtime_wheel_contact_response_check` now covers:

- a non-trivial exact `FUN_007af0a0` response-input transform;
- the existing explicit-input `FUN_00766510` path;
- the new BODY-source join using the proven `+0xd4` / `+0x18` source locations;
- parity of response gain, response vector, and auxiliary response across the joined boundary;
- non-finite source rejection through the shared transform implementation.

`native-physics-recent` now verifies `response_input_transform_proven=true` and covers Phases 656–663.

## Next boundary

The next source-backed target is the caller-side application of the generated primary response vector: Phase 371 records that the response is transformed back through the BODY pose and passed to `FUN_007baa70`. That join should be ported only from exact source-visible transform/input arguments, without assigning force/torque names or introducing pose integration.
