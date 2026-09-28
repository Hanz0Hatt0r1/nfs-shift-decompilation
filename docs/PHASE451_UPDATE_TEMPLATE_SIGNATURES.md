# Phase 451 — specialized-provider update template signatures

## Goal

Phase 451 classifies assignment-level update templates after source-context resolution.

For the common retail form `destination = destination - source * factor`, the runtime records the structural template `self-subtract-product`. The scaled variant is recorded separately as `self-subtract-product-then-scale` when the first RHS reference is the same absolute storage address as the destination.

Assignments that do not repeat their destination on the RHS remain generic `subtract-product`/`subtract-product-then-scale` forms. Pivot scaling and other operator classes remain those established by Phase 443.

## Why this matters

The new layer links four proven properties without copying the retail expression:

`pivot -> destination -> ordered RHS dependencies -> operator/template`

This exposes the characteristic update shape needed for a numerical reimplementation while keeping packed-address aliasing explicit through Phase 450.

## Interpretation boundary

`self-subtract-product` is a source-structure label. It is not by itself a claim that the operation is a Schur-complement update, LDLᵀ factorization step, or any other named mathematical operation.

Numeric coefficients, compiler temporaries, physical units, semantic matrix names and provider class identity remain outside this phase.

Run locally with:

    python specialized_provider_update_template_runtime.py SHIFT.exe.c
