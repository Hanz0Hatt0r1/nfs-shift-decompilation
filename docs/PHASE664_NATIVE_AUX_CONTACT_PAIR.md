# Phase 664 — native FUN_00766510 auxiliary-contact pair

Phase 664 closes the source-backed two-call orchestration near the end of `FUN_00766510`.

Phase 374 established that the caller invokes `FUN_00758fc0` for exactly two records at:

- `this + 0x37d8`;
- `this + 0x3858`.

Phase 659 already ports the full arithmetic and BODY-accumulator application performed by one `FUN_00758fc0` record. Phase 664 composes those existing native calls in caller order while carrying the BODY accumulator from the first call into the second.

## Native boundary

`execute_fun_00766510_aux_contact_pair()` consumes the shared source-visible inputs:

- BODY frame;
- BODY point-transform state;
- current BODY accumulator state;
- caller reference point;
- exactly two `AuxContactRecord` values corresponding to offsets `0x37d8` and `0x3858`.

For each record it delegates to the existing `execute_fun_00758fc0_aux_contact_response()` implementation. The second record always sees the accumulator state produced by the first record. Inactive or nonnegative-Z records retain the existing Phase 659 fail-closed/no-application behavior.

The native contract freezes the count and offsets as:

```text
record_count = 2
record_offsets = [0x37d8, 0x3858]
```

## What this does not claim

This phase does not assign physical names to the two records, the caller reference point, or any response fields. It also does not schedule the pair in `NativeRuntimeState`; the ownership/timing of the containing `FUN_00766510` path remains a separate integration boundary.

The primary `FUN_007551e0` response-application transform is still not frozen by the current evidence contracts. Phase 664 intentionally does not guess that transform merely because the auxiliary path already reaches `FUN_007baa70`.

## Regression

`shift_runtime_aux_contact_pair_check` verifies:

- the exact two source offsets;
- both active records execute in sequence;
- the first BODY accumulator is carried into the second call;
- paired contributions accumulate deterministically;
- an inactive second record preserves the first call result;
- an entirely inactive pair preserves the incoming BODY accumulator.

`native-physics-recent` now executes and verifies Phases 656–664.
