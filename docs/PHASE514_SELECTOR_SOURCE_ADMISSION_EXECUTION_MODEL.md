# Phase 514 — selector source admission execution model

## Goal

Turn the Phase 513 source-backed admission ordering into a small executable
state model that can be regression-tested without claiming undocumented
gameplay semantics.

Contract:

`SHIFT.VehiclePhysicsSelectorSourceAdmission/1`

## State transition

For a source record token at `source_record+0x10`:

1. derive `selector_key = token & 0xf`;
2. derive `bit_mask = 1 << selector_key`;
3. admit only when `owner+0x4f0 & bit_mask != 0`;
4. on a mask hit, call `thunk_FUN_00409290(&DAT_00bbc600, source_record)`;
5. clear the same owner mask bit with XOR;
6. inside the descriptor wrapper, increment the descriptor count only when
   `context+0x1c < context+0x28`.

The executable model therefore distinguishes **mask admission** from
**descriptor population success**.

## Important edge case

When the admission bit is set but selector capacity is exhausted, the model
records:

- wrapper called;
- population not successful;
- admission bit cleared;
- descriptor count unchanged.

That follows the observed separation between the upstream mask branch and the
wrapper's independent capacity condition.

## Evidence boundary

The implementation remains structural. The low-nibble value is kept as an
observed routing key; no gameplay category, provider identity, or semantic
meaning is assigned to it.
