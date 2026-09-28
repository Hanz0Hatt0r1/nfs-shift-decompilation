# Phase 472 — specialized-provider input footprint

## Goal

Phase 472 intersects source-derived first-read addresses from Phase 456 with the canonical reset domain from Phase 480.

The result answers: **which workspace addresses are read by the provider solver before that solver writes them, and were those addresses initialized by the provider reset path?**

## Classification

`reset-zero` — first-read address lies in the canonical reset-zero domain.

`reset-unit` — first-read address is one of the pivot `1.0` seed slots.

`caller-input-candidate` — workspace first-read address is outside the canonical reset-touched domain.

`external-or-upstream` — first-read address is outside the provider workspace/output vector.

## Correction carried forward

The reset-touched domain is not computed from direct zero stores alone. It includes reset bulk-clear ranges and the separate unit-seed set. This prevents provider 1's bulk-reset operations from being misclassified as caller inputs.

## Why this matters

Phase 469 measures what a real pre-solve capture contains relative to this domain. Phase 472 supplies the static boundary for identifying strongest caller-population candidates without inventing a logical matrix layout.

## Important limitation

`caller-input-candidate` does not mean `matrix element`. Packed workspace aliases remain possible, and an upstream function may populate a shared staging slot before the provider solve.

## Scope boundary

The footprint remains an address-level reconstruction. It does not assign matrix semantics, physical units, or provider class identity.
