# Phase 490 — scalar-reset evidence manifest

## Goal

Phase 490 composes the complete scalar-reset runtime evidence stream into one deterministic per-frame manifest.

The manifest consumes `scalar_reset_events.jsonl` from Phase 485/487 and optionally provider pre-solve captures from Phase 463.

## Included checks

- scalar event schema validation;
- exact callsite/group ordering validation from Phase 488;
- per-frame provider/backend counts;
- per-frame group counts and observed selector sequence;
- reset-event counter reconciliation with provider solve snapshots from Phase 489.

## Per-frame output

Each frame record contains:

- event count;
- provider/backend counts;
- source group counts;
- selector sequence;
- global call indices;
- selector min/max.

## Why this matters

This is the first single artifact that exposes the complete reset phase from runtime capture: which source group produced each call, which selector was supplied, and how far the reset stream had progressed when the provider solve snapshot was taken.

That makes later comparisons against provider workspace mutations and numerical behavior much easier to automate.

## Scope boundary

The manifest is still an evidence aggregator. It does not infer matrix semantics, constraint names, physical units, or provider class identity. A complete event log is required for strict counter reconciliation.