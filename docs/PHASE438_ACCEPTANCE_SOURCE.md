# Phase 438 — acceptance RLE source extractor

Phase 438 adds a source-level extractor for the strict-upper-triangle
acceptance arrays embedded directly in the retail provider comparison helpers.

## Provider 0

FUN_007c6e50 stores its signature in local_b4[0..82], for 83 run entries. The
runs plus their transition cells cover exactly 780 strict-upper cells for the
40-scalar domain.

## Provider 1

FUN_007cdb40 stores its signature in local_e4[0..106], for 107 run entries. The
runs plus their transition cells cover exactly 561 strict-upper cells for the
34-scalar domain.

## Validation role

The extractor compares the arrays recovered from a local SHIFT.exe.c against
the static signatures in specialized_provider_runtime.py. This gives a
repeatable audit path from the actual retail source to the provider matcher
without committing the proprietary source itself.
