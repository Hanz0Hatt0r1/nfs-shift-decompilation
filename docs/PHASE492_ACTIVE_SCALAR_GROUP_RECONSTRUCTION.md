# Phase 492 — active scalar group reconstruction

## Goal

Phase 492 reconstructs the active scalar groups represented by the runtime `FUN_007b2210` reset events.

Each enabled constraint record emits a fixed-width selector sequence:

- JOINT/HINGE: `base`, `base+1`, `base+2`;
- SECONDARY: `base`, `base+1`;
- BAR: `base`.

The exact callsite attribution from Phase 486 tells the analyzer which ordinal belongs to each event.

## Result

For each frame and active source group, the analyzer emits:

- source group;
- width;
- `base_selector`;
- complete selector list.

Repeated records are represented as separate entries, so the runtime event stream becomes a concrete sequence of active scalar ranges.

## Validation

The analyzer rejects:

- missing callsite attribution;
- invalid group/ordinal combinations;
- incomplete fixed-width records;
- selector sequences that are not contiguous from the reconstructed base.

## Why this matters

This is the first runtime reconstruction of the scalar index assignment produced by the constraint loops. It can be used later to correlate active constraint records with the provider's 40- or 34-scalar domain.

## Scope boundary

`base_selector` is an index-level runtime fact. It is not renamed as a matrix row, constraint type, physical degree of freedom, or other semantic quantity without additional evidence.