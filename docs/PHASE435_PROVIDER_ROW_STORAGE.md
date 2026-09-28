# Phase 435 — exact provider row-pointer topology

Phase 435 decodes the pointer tables populated by FUN_007d2f70 and
FUN_007cd980.

## Provider 0

There are exactly 40 row pointers beginning at 0x00C21698. The first pointer is
0x00C21738, which is the factor workspace base. The final row segment ends at
the output vector base 0x00C23C68.

The 40 segment extents, expressed as double counts, are:

    25,25,22,27,27,30,25,22,27,20,
    25,25,22,27,27,30,25,22,27,40,
    40,40,40,40,37,37,37,37,37,30,
    30,30,30,30,27,27,27,27,27,40

They sum exactly to 1190 doubles.

## Provider 1

There are exactly 34 row pointers beginning at 0x00C1FDB0. The final row
segment ends at output vector base 0x00C21588.

The segment double counts are:

    22,22,22,22,22,22,22,22,22,12,
    19,19,19,19,29,34,34,16,16,16,
    34,16,16,24,24,24,24,24,19,19,
    19,19,19,34

They sum exactly to 746 doubles.

## Interpretation

These numbers authenticate the static storage extents used by the provider.
They should not be equated directly with the matrix sparsity signature from
Phase 431. The provider's unrolled solver may use a compact index stream inside
each row segment, so the next decoding target is the per-segment index encoding
and its relation to the solver's sparse traversal.
