# Phase 482 — reset-delta semantic correction

## Problem

Phase 469 had already switched its reset classification to the canonical Phase 480 touched domain, but its `cleanup_reset_equivalent` field still read the legacy `reset_zero_cleanup_exact_match` flag.

That legacy flag is intentionally false when unit-diagonal seed slots are separate from reset-zero slots, even when the complete reset touched domain exactly reconstructs cleanup coverage.

## Fix

Phase 482 changes `cleanup_reset_equivalent` to consume `cleanup_reconstructed_from_reset`, and exposes `cleanup_reset_partition_disjoint` in the reset-delta summary.

Therefore the reset delta now distinguishes:

- reset-zero subset of cleanup;
- unit-diagonal seed coverage;
- full cleanup-domain reconstruction;
- disjointness of zero and seed sets.

## Consequence

A correct provider reset partition no longer appears as a cleanup mismatch in Phase 469-derived reports.

The numeric/live-capture status remains unchanged: this is a storage-domain semantic correction only.

## Scope boundary

No matrix semantics, provider class identity, or physical unit is inferred.
