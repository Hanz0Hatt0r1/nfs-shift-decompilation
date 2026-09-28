# Phase 441 — specialized-provider RHS reference stencils

## Goal

Phase 441 extends the Phase 440 workspace write graph by recovering the **address-level data references on the RHS of solver assignments**.

The retail arithmetic expression itself is not stored in the repository. Instead, each assignment is represented as a destination plus normalized references to the workspace, output vector, or unresolved global data.

## Reconstructed reference forms

The extractor recognizes the source forms observed in the specialized provider solvers:

- direct `DAT_xxxxxxxx` references;
- row-pointer base/offset references using `local_10 * 4`;
- flat `local_10 * 8` pointer references;
- flat array references `(&DAT_xxxxxxxx)[local_10]`.

Loop iterations are expanded and every resolved address is mapped against the exact Phase 435 row-segment topology. Addresses in the output-vector range are mapped to output-vector indices; everything else remains an explicit global address.

## Cross-phase validation

For every provider, the extractor compares the number of workspace destinations with Phase 440's workspace write-site count. Missing or extra workspace assignments block validation.

Workspace references must resolve to an explicit `(row, column)` pair. The extractor also preserves the order in which normalized references occur in the source assignment, including mixed direct and loop-indexed forms.

## Scope boundary

This is a **data-dependency stencil**, not yet a numeric solver implementation. It does not emit the proprietary RHS expression text, compiler temporaries, inferred matrix names, or physical units. A later phase can use these stencils to reconstruct fixed-layout update operators while retaining the retail implementation as the evidence source.

## Local retail audit

Run against the supplied local decompilation source with:

    python specialized_provider_rhs_stencil_runtime.py SHIFT.exe.c

The source contract requires 40 unique pivots for provider 0 and 34 for provider 1. The repository deliberately does not include the proprietary `SHIFT.exe.c` itself.
