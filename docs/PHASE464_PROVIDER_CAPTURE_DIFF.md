# Phase 464 — specialized-provider pre/post capture diff

## Goal

Phase 464 adds a raw-storage differential view for `provider_pre_*` and `provider_post_*` snapshots produced by Phase 463.

The comparator reports every changed packed-workspace double and output-vector double by absolute address, including before/after values and absolute/relative delta.

## Structural checks

The comparator requires matching provider id, scalar count and workspace size. When both snapshots contain row-pointer tables, every pointer must remain unchanged across the solve.

Output-vector indices are checked against the provider scalar domain. Changed-address count is cross-validated against the emitted address list.

## Why this matters

This is the first capture-side measurement of the provider's actual write footprint. It can now be compared directly with source-derived Phase 447/451 update relations without converting packed addresses into guessed logical matrix cells.

## Interpretation boundary

A changed workspace slot is only a storage mutation. It is not automatically a factor coefficient, matrix element, RHS value, or semantic state variable. Alias resolution remains a separate Phase 448–450 layer.

The diff also does not assert numeric retail parity; it only describes the observed pre/post mutation.
