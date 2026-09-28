# Phase 469 — specialized-provider reset delta analyzer

## Goal

Phase 469 compares a real provider `pre-solve` capture against the source-backed reset state established by Phases 466, 468 and the canonical reset-domain helper from Phase 480.

The analyzer works on absolute provider storage addresses and produces four categories:

- `unchanged-reset-state` — observed value still matches the reset baseline;
- `reset-zero-slot-deviation` — a canonical reset-zero slot was populated/modified;
- `reset-unit-slot-deviation` — a pivot seed no longer equals the reset `1.0`;
- `outside-reset-domain-nonzero` — a packed workspace slot outside the canonical reset domain became non-zero.

Output-vector entries are treated separately as `output-nonzero`.

## Reset-domain source

The analyzer now uses `SHIFT.SpecializedProviderResetDomainRuntime/1`, which includes reset bulk-clear ranges as well as direct zero assignments. Unit-diagonal seed slots are tracked independently and are not treated as zero slots merely because they are reset storage.

Cleanup equality from Phase 468 is retained as metadata. Provider 1's documented 280-slot reset-zero subset of a 314-slot cleanup domain does not block reset-delta analysis.

## Why this matters

This gives the direct measurement point for the transition:

`reset state → caller-populated provider state → provider solve entry`

Only workspace slots outside the canonical reset-touched domain are classified as caller-population candidates by later phases.

## Conservative semantics

An outside-reset-domain workspace value is not an error. It is a signal that the caller or an earlier runtime path populated storage not covered by reset. A reset-slot deviation is likewise a measured difference from the source-backed baseline, not automatically a bug.

## Scope boundary

The analyzer reports storage facts and does not assign matrix coordinates, physical quantities, or provider semantics.
