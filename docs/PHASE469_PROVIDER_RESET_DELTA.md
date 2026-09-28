# Phase 469 — specialized-provider reset delta analyzer

## Goal

Phase 469 compares a real provider `pre-solve` capture against the source-backed reset state established by Phases 466–468.

The analyzer works on absolute provider storage addresses and produces four categories:

- `unchanged-reset-state` — observed value still matches the reset baseline;
- `reset-zero-slot-deviation` — a known reset-zero slot was populated/modified;
- `reset-unit-slot-deviation` — a pivot seed no longer equals the reset `1.0`;
- `outside-reset-domain-nonzero` — a packed workspace slot outside the proven reset domain became non-zero.

Output-vector entries are treated separately as `output-nonzero`, because both providers prove complete output-vector zeroing during reset.

## Why this matters

This gives the first direct measurement point for the transition:

`reset state → caller-populated provider state → provider solve entry`

A future real provider capture can therefore reveal exactly which packed slots are populated before `FUN_007c7200` or `FUN_007cdfc0` starts.

## Conservative semantics

An outside-reset-domain workspace value is not an error. It is a signal that the caller or an earlier runtime path populated storage not covered by the reset helper. Likewise, a reset-slot deviation is not automatically a bug; it is simply measured divergence from the source-derived reset state.

The analyzer reports storage facts and does not assign matrix coordinates, physical quantities, or provider semantics.

## Scope boundary

The reset baseline remains a static source-derived model until a real Phase 463 provider capture supplies the corresponding runtime snapshot. Numeric provider parity remains a separate differential gate.
