# Phase 387 — Sparse constraint solver execution

`FUN_007b0f20` is the consumer of the compact constraint graph emitted by `FUN_007b1360`. This phase records its traversal and storage contract without assigning undocumented physical meaning to the matrix coefficients.

## Inputs

The solver receives the matrix as a row-pointer array, a writable double vector, and the solver variable count. The graph object contains four pointers at offsets `+0x00`, `+0x04`, `+0x08` and `+0x0c`: forward outer records, reverse outer records, edge-record pool and byte dependency lists.

## Forward pass

For `i = 0..n-1`, the first edge attached to `forward[i]` supplies lower dependencies used before computing the diagonal reciprocal `1 / row_i[i]`. Remaining forward edge records update later rows. The terminal `forward[n]` record subtracts lower dependencies from the RHS and applies the diagonal scale.

## Backward pass

The reverse table is traversed from `n-2` down to `0`. Each record identifies the upper dependencies that are subtracted from the current RHS entry. The `n-1` reverse record is allocated but not traversed by the back-substitution loop.

## Record layout

Each outer record is 8 bytes: a 32-bit item count and a 32-bit item pointer. Each edge item is also 8 bytes: node byte at `+0x00`, dependency count byte at `+0x01`, and a 32-bit dependency pointer at `+0x04`. Dependency indices are byte-sized.

## Provider bypass

After the matrix/graph preparation, `FUN_007b3f40` bypasses `FUN_007b0f20` when a provider exists at physics-system `+0x48`; in that case it invokes the provider virtual method at `+0x18` instead.

## Remaining unknown

The sparse execution boundary is now explicit. The remaining unknown is the numeric coefficient population in `FUN_007ba2b0` and the provider-specific implementation of the `+0x18` solver hook.
