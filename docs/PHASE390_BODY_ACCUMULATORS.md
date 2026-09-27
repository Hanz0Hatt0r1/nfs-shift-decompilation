# Phase 390 — SDF body accumulators

`FUN_007bb8d0` initializes the per-body solver accumulator storage used by the subsequent frame-stage routines.

## Storage layout

The body runtime object owns four related solver-contribution regions:

- `+0x150`: solver-vector contribution buffer, count at `+0xa4`;
- `+0x154`: flat solver-matrix contribution buffer, count at `+0xa8`;
- `+0x158`: pointer table, count at `+0xac`;
- `+0x15c`: source row-index vector feeding the pointer table.

Every frame, the function clears the solver-vector and solver-matrix contribution regions and reconstructs each matrix row pointer as `+0x154 + row_index[i] * 8`.

## Hinge refresh

The same routine walks the hinge sample array at `+0x164` with stride `0xA0`. For samples whose byte flag at `+0x98` is nonzero, it calls `FUN_007aefb0` using the negative body pointer and negative sample pointer and writes the resulting transform into the body transform region.

The implementation keeps the solver vector/matrix contribution regions as raw storage coordinates. Generation of the row-index vector and the physical meaning of their coefficients are separate evidence targets.
