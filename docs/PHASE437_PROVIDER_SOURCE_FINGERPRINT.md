# Phase 437 — specialized-provider source fingerprint

Phase 437 adds a small static-source parser that can regenerate the structural
fingerprint of the two unrolled provider solver functions from SHIFT.exe.c.

## Extracted structure

For each provider solver, the extractor finds every unique reciprocal pivot
expression of the form:

    1.0 / _DAT_xxxxxxxx

It then assigns the source block beginning at that pivot until the next unique
pivot and extracts the local_10 loop ranges occurring inside that block.

This gives a reproducible source-level fingerprint without copying the full
retail decompilation into the repository.

## Why this is useful

The previous phases already proved:

- provider 0 has 40 unique reciprocal pivots;
- provider 1 has 34 unique reciprocal pivots;
- pivot i is stored at row_pointer[i] + 8*i.

Phase 437 adds a regeneration mechanism so later edits to the solver runtime can
be checked against the actual source layout instead of relying only on hand
entered metadata.

The parser is intentionally structural. It does not claim that a loop range by
itself is a semantic dependency list, and it does not rewrite the proprietary
coefficient expressions.
