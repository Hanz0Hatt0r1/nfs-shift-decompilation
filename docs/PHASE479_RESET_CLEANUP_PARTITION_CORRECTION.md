# Phase 479 — reset/cleanup partition correction

## Correction

Phase 479 fixes two issues in the earlier reset/cleanup comparison.

First, the reset parser previously stopped at the closing brace of the inner `switch`, so it could undercount the provider reset cases. The parser now uses balanced-brace extraction and correctly sees all `0..39` / `0..33` cases.

Second, reset `0` writes were incorrectly compared directly with the full cleanup domain. The correct storage identity is:

`cleanup domain = reset-zero domain ∪ unit-diagonal seed domain`

with the two sets disjoint.

## Verified source results

Against the supplied retail `SHIFT.exe.c` source:

Provider 0:

- reset cases: **40**;
- reset-zero slots: **370**;
- unit-diagonal seed slots: **40**;
- cleanup-covered slots: **410**;
- union equality: exact;
- zero/seed overlap: none.

Provider 1:

- reset cases: **34**;
- reset-zero slots: **280**;
- unit-diagonal seed slots: **34**;
- cleanup-covered slots: **314**;
- union equality: exact;
- zero/seed overlap: none.

Workspace/output split is also exact: provider 0 has 370 reset-zero workspace slots plus 40 output slots; provider 1 has 280 reset-zero workspace slots plus 34 output slots.

## Consequence

The earlier wording that reset zero writes alone reproduced the cleanup domain was too strong and is removed. The corrected model distinguishes the cleanup baseline from the selector-driven reset's zero and unit-seed writes.

## Scope boundary

This remains a storage-level identity. It does not infer matrix semantics, provider class names, or physical units, and it does not make reset a per-frame initializer.
