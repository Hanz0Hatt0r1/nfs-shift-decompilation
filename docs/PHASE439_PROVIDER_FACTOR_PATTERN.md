# Phase 439 — specialized-provider factor pattern extraction

Phase 439 extracts the future-column factor pattern from the fully unrolled
provider solver source.

For each pivot i, the parser isolates the source block beginning at the
corresponding reciprocal pivot and identifies writes into the current row's
static workspace segment. Loop-based writes contribute every column in their
local_10 range; direct global writes contribute their exact double-column.

Only columns greater than the pivot index are retained. This produces the
provider's post-pivot factor edge set without copying the proprietary source.

The same pass validates the exact diagonal geometry from Phase 436:

    pivot_diagonal = row_pointer[i] + 8*i

The factor pattern is deliberately kept structural. It is not described as a semantic matrix graph until the source update schedule and packed storage dependencies are cross-checked against these extracted future-column sets.

Phase 446 corrected the extractor so the logical scalar-domain bound is the provider dimension, not the byte extent between adjacent row pointers. The latter is storage topology and may be crossed by an explicit factor loop.
