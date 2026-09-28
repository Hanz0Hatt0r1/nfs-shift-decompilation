# Phase 481 — reset parser hardening and canonical reset partition

## Fixes

Phase 481 fixes the reset parser so nested braces cannot truncate provider reset functions. The parser now extracts a balanced outer function body before locating `case` blocks.

The canonical Phase 480 reset-domain layer remains the single source for reset zero/seed storage sets. It now explicitly validates that zero slots and unit-diagonal seed slots are disjoint.

Phase 481 also rewires the reset/cleanup comparison to consume `extract_reset_domain()` rather than rebuilding reset sets locally.

## Verified source result

Directly against the supplied retail `SHIFT.exe.c`:

Provider 0: 40 reset cases, 370 reset-zero slots, 40 unit-diagonal seeds, 410 cleanup-covered slots, exact union, zero/seed overlap 0.

Provider 1: 34 reset cases, 280 reset-zero slots, 34 unit-diagonal seeds, 314 cleanup-covered slots, exact union, zero/seed overlap 0.

The provider workspace/output split is 370/40 for provider 0 and 280/34 for provider 1.

## Consequence

The reset state is now represented consistently as two disjoint write domains:

`reset-zero` — direct zero writes plus reset bulk-clear coverage;

`unit-diagonal` — one exact `1.0` seed per reset selector case.

`reset-touched = reset-zero ∪ unit-diagonal`

Cleanup coverage is checked against this full touched domain.

## Scope boundary

This remains a storage-level reconstruction. It does not identify logical matrix coefficients, physical units, or the C++ provider class hierarchy.
