# Phase 446 — specialized-provider factor pattern correction

## Problem found

Phase 439 used the distance from `row_pointer[i]` to `row_pointer[i+1]` as a hard upper bound for logical factor columns. Retail inspection showed that explicit factor loops can cross that storage extent: for example, late pivots use `local_10` values beyond the adjacent-pointer span while still writing the current pivot's normalized factor row.

At the same time, blindly accepting every direct address in the larger absolute address range is unsafe because packed workspace addresses can alias cells belonging to another logical stage.

## Corrected rule

The corrected extractor uses the source structure itself:

1. isolate the pivot block;
2. stop at the first output-vector update;
3. accept loop-based LHS writes whose base is exactly the current pivot row pointer and whose `local_10` index is a future scalar in the provider domain;
4. accept direct LHS stores only while they are inside that same normalization prefix and carry the pivot-local `dVar1` scale;
5. do not use adjacent row-pointer distance as a logical column bound.

This preserves the explicit scalar indices emitted by the retail unrolled source while avoiding later packed-address aliasing.

## Validation

Regression coverage now includes a factor loop whose indices extend beyond the old segment extent and a direct factor store beyond that extent. A post-output assignment with the same scale variable is excluded.

The Phase 436 diagonal relation remains unchanged:

    pivot_diagonal = row_pointer[i] + 8*i

## Interpretation boundary

The provider row-pointer spans remain storage topology. They are not treated as independent logical matrix rows or as a guaranteed column-capacity bound.
