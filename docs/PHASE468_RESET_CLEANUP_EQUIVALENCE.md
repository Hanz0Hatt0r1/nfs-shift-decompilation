# Phase 479 — correction: complete reset-zero domain

Phase 479 corrects the Phase 468 reset/cleanup comparison after a source audit found that reset cases also contain `FUN_0040cec0` bulk-clear operations.

## What was wrong

Phase 468 compared cleanup coverage with only direct `DAT_xxxxxxxx = 0` reset stores. That omitted reset bulk-clear intervals and also treated the `1.0` diagonal seed as though it were itself a zeroed slot.

## Correct model

The reset-zero domain is the union of:

- direct zero assignments in every reset case;
- every 8-byte slot covered by reset `FUN_0040cec0` bulk clears.

Unit-diagonal seed addresses are tracked separately.

## Verified results from the retail source

Provider 0:

- reset-zero domain: **410** slots;
- cleanup zero domain: **410** slots;
- exact equality: **yes**;
- unit-diagonal seeds: **40**;
- every unit seed is inside the cleanup zero domain.

Provider 1:

- reset-zero domain: **280** slots;
- cleanup zero domain: **314** slots;
- exact equality: **no**;
- reset-zero is a strict subset of cleanup by **34** slots;
- unit-diagonal seeds: **34**;
- every unit seed is inside the cleanup zero domain;
- unit-diagonal seeds are not required to belong to the reset-zero domain.

## Consequence

The earlier Phase 468 claim of complete reset/cleanup zero-set equivalence for provider 1 is withdrawn. The corrected contract preserves the observed subset mismatch instead of hiding it behind a false readiness condition.

Provider 0 remains an exact zero-domain match.

## Scope boundary

This remains a storage-level comparison. It does not infer logical matrix semantics or claim that reset is a per-frame initializer.
