# Phase 403 — retail SDF matrix storage

`FUN_007b3820` allocates the global sparse-solver matrix as `scalar_count * scalar_count * 8` bytes and the row-pointer table as `scalar_count * 4` bytes. It then initializes each row pointer to `matrix_base + scalar_count * row * 8`.

`FUN_007b2010` clears every row through the row-pointer table before the coupling passes run. `FUN_007bb8d0` reconstructs per-body row pointers from the compact `+0x15c` row-index vector with the same `matrix_base + row_index*8` formula.

The new runtime helpers materialize the logical matrix pool, row indices and row pointers together, and validate that the three views address identical cells. This keeps the Phase 402 dense logical assembler while adding a source-faithful storage representation for later captured-value comparison.

The canonical row index for scalar row `i` is `scalar_count * i`, so the row width is exactly the global solver scalar count. The physical pointer value itself remains an address-level construct and is represented symbolically via a supplied base address in tests.
