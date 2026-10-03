# Phase 675 — native four-wheel spring-gap batch

Phase 675 composes the already-native Phase 669 `FUN_00758b50` wheel-kinematics
pre-helper boundary with the Phase 671 `FUN_00755950 -> FUN_007555b0` spring-gap
join across the exact four-wheel loop recovered in Phase 364.

No new physical semantics are introduced.  Unknown spring inputs remain explicit
inputs and the unresolved x87 value stored by the retail caller at runtime
`+0x548` remains outside this contract.

## Source-backed ordering

The recovered `FUN_00758b50` loop visits exactly four wheel-state blocks:

```text
wheel state base = vehicle + 0x848
stride           = 0xA80
count            = 4
order            = 0, 1, 2, 3
```

For each slot, retail first checks block `+0xF8`.  A non-zero value skips the
relative-vector construction and therefore also skips `FUN_00755950` and
`FUN_007555b0` for that slot.

The native batch preserves that control-flow order exactly:

```text
slot +0xF8 gate
  -> prepare_fun_00758b50_wheel_kinematics()
  -> distance_error = reference_length - relative_length
  -> stored_projection = -projection_input
  -> execute_fun_00755950_spring_gap_join()
  -> FUN_007555b0 gap/history state
```

The batch never evaluates downstream payload for a skipped slot.  This is tested
with a skipped zero relative vector that would fail normalization if the gate were
moved later.

## Typed contract

`WheelSpringGapBatchSlotInput` carries only values already required by the proven
single-wheel boundaries:

- `WheelKinematicSlotInput` including the source skip gate;
- spring type;
- lower and upper helper boundaries;
- previous/current-gap input state.

`execute_fun_00758b50_spring_gap_batch()` accepts
`std::array<..., 4>`, so the native boundary cannot admit an invalid wheel count.
The Python oracle rejects any sequence whose length is not exactly four.

The result exposes:

- a fixed four-slot processed mask;
- optional kinematic and spring results per source slot;
- exact processed count;
- explicit processed-order entries, valid through `processed_count`.

## Fail-closed behavior

For every active slot, the composed existing kernels reject:

- NaN or infinity in consumed kinematic/spring scalar inputs;
- zero-length relative vectors;
- negative spring type;
- mismatched cross-contract wheel topology or scalar handoff.

Skipped slot payload is intentionally not consumed because the source gate occurs
before those reads.  This preserves retail control flow rather than validating
values retail does not touch on that path.

## Reference oracle and regression

`src/physics/wheel_spring_gap_batch_runtime.py` is the Python reference oracle.
Its deterministic regression uses active slots `0`, `2`, and `3`, with slot `1`
skipped, and freezes:

- retail processed order `0,2,3`;
- exact relative lengths `5`, `2`, `3`;
- displacements `2`, `-1`, `7`;
- crossing and non-crossing helper paths;
- trigger writes `1.5` and `4.0` on the two crossing cases;
- absence of invented writes on the non-crossing case.

`shift_runtime_wheel_spring_gap_batch_check` mirrors those exact fixtures and
adds fail-closed active Inf, negative spring-type, and zero-vector cases.

## Explicit non-claims

Phase 675 does **not**:

- reconstruct the unresolved x87 return consumed into runtime `+0x548`;
- assign spring-force, tyre-force, or suspension-unit semantics;
- execute the final `FUN_007baa70` / `FUN_007baaf0` application vectors;
- schedule `FUN_00758b50` in `NativeRuntimeState`;
- infer the two-pass `FUN_00770e80` frame scheduler;
- claim a persistent chassis pose writer.

The next native step remains evidence-gated.  A useful follow-up requires either
an exact final per-wheel application-vector producer or a fully proven scheduler /
persistent-state boundary from the static process; neither is synthesized here.
