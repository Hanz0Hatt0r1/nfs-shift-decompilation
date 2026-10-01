# Phase 625 — native BODY sparse row-index storage

Phase 624 produces the complete prepared BODY-local lower-triangle matrix as a
logical dense view. Phase 625 maps that view through the source-backed
`FUN_007bb8d0` storage contract.

## Retail storage boundary

Per BODY:

- matrix pool: `BODY+0x154`;
- row-pointer table: `BODY+0x158`;
- row-index vector: `BODY+0x15c`.

The recovered pointer formula is:

```text
row_pointer[i] = BODY+0x154 + row_index[i] * 8
```

Phase 625 represents physical pointers as byte offsets from the matrix pool
rather than inventing process addresses.

## Native API

New files:

- `native_runtime/include/shift_body_sparse_matrix_storage.hpp`;
- `native_runtime/src/body_sparse_matrix_storage.cpp`;
- `native_runtime/tests/body_sparse_matrix_storage_check.cpp`.

`materialize_fun_007bb8d0_sparse_rows()` accepts:

- the Phase 624 logical lower matrix;
- solver scalar count;
- explicit prepared row indices;
- exact matrix-pool double count.

It validates:

- square matrix shape;
- finite values;
- one row index per scalar row;
- every row span fits the supplied pool;
- physical row spans do not alias;
- the logical source contains no upper-triangle writes.

It then materializes only lower-domain cells through each prepared row offset.

## Noncanonical-row oracle

The six-scalar Phase 624 matrix is remapped through:

```text
row_indices = [18, 0, 30, 6, 24, 12]
```

for a 36-double pool.

Expected row-pointer byte offsets are:

```text
[144, 0, 240, 48, 192, 96]
```

Every logical cell read back through the row mapping must match the original
lower-triangle matrix, while every upper-triangle cell remains zero.

The checker also proves:

- all 21 lower-domain cells are addressed;
- all 21 fixture lower cells are non-zero and written;
- aliased row spans are rejected;
- out-of-range row spans are rejected;
- upper-triangle source writes are rejected.

## Boundary after Phase 625

Phase 625 closes the prepared `BODY+0x154/+0x158/+0x15c` storage mapping for
Phase 624 contributions.

Still open:

- authentic `FUN_007b3ed0` sample refresh/input production;
- direct Phase 624→625→`FUN_007ba570` generated-contribution join on each
  admitted fixed step;
- runtime reset-node selection;
- authentic matrix/RHS observations;
- provider-present dispatch;
- persistent vehicle transform/motion integration.

No coefficient or physical-state semantics are introduced by this phase.
