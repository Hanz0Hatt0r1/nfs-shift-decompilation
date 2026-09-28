# Phase 472 — specialized-provider input footprint

## Goal

Phase 472 intersects the source-derived first-read footprint from Phase 456 with the exact reset domain from Phases 466–468.

The result answers a narrow but important question: **which workspace addresses are read by the provider solver before that solver writes them, and were those addresses initialized by the provider reset path?**

## Classification

`reset-zero`
— first-read address lies in the reset zero domain.

`reset-unit`
— first-read address is one of the pivot `1.0` seed slots.

`caller-input-candidate`
— workspace first-read address is outside the proven reset domain. This is the strongest static candidate for data supplied by an upstream caller or runtime stage.

`external-or-upstream`
— first-read address is outside the provider workspace/output vector.

## Why this matters

Phase 469 shows that reset initializes only a subset of packed workspace slots. Phase 472 now identifies which of the remaining slots are actually consumed before the solver overwrites them.

This is the cleanest static boundary currently available for reconstructing the provider's caller-populated state without inventing a logical matrix layout.

## Important limitation

`caller-input-candidate` does not mean `matrix element`. Packed workspace aliases remain possible, and an upstream function may populate a shared staging slot before the provider solve. Only a real capture can establish the runtime value and provenance.

## Next use

Once Phase 463 provides a real provider pre-solve snapshot, the footprint can be intersected with the actual nonzero/populated slots from Phase 469 to identify the strongest runtime-supported input candidates.
