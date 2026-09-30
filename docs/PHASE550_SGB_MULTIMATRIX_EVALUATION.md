# Phase 550 — source-backed SGB MultiMatrix evaluation

Phase 550 reconstructs the static numeric update performed by the retail
`RenderHierarchy/MultiMatrix.cpp` path. It closes the arithmetic that Phase
548 intentionally left unresolved, while preserving the real runtime root
matrix as an explicit input instead of assuming identity.

## Runtime layout

`FUN_006b144b` allocates `matrix_count * 0x90` bytes and splits the block
into three arrays:

- local matrices: `matrix_count * 0x40`;
- runtime/world matrices: `matrix_count * 0x40`;
- descriptors: `matrix_count * 0x10`.

Each descriptor stores the world-slot pointer at `+0x00`, mode at `+0x08`,
the parent byte at `+0x0b`, and the self index at `+0x0c`. Construction
initializes every descriptor mode to 1.

## Local MATRIX construction

`FUN_0068cbb0` consumes the already-decoded MATRIX record:

- WXYZ quaternion;
- XYZ offset;
- uniform scale;
- signed parent dword.

It stores only the low byte of `parent` in descriptor `+0x0b`, builds the
4x4 local matrix through `FUN_00445ec0`, scales the 3x3 basis and writes
translation at float indices 12..14. The local matrix is initially copied to
the matching world slot.

## Runtime update

The owner update paths `FUN_006ab710` (HIERARCHY) and `FUN_006b4280`
(LOD) first overwrite **world slot 0** with a caller-provided root matrix.
They then call `FUN_006b1620`.

For the default/static descriptor mode 1, `FUN_006b1620` processes slots
1..N-1 in source order. `FUN_00401610/FUN_00401619` proves the D3D
row-vector multiplication order:

```text
world[i] = local[i] * world[parent_low_byte]
```

The evaluator therefore cannot replace the root input with the serialized
local slot 0 after a runtime update.

## Implementation

`src/scene/sgb_multimatrix.py` adds
`SHIFT.SGBMultiMatrixEvaluation/1`.

The evaluator:

- reproduces `FUN_0068cbb0` local-matrix construction;
- reproduces the row-major matrix multiply used by
  `FUN_00401610/FUN_00401619`;
- preserves source-order evaluation;
- applies the low-byte parent rule;
- requires an explicit 4x4 root world matrix;
- fails closed on absent roots, malformed records and out-of-range parents.

Without a root matrix it still emits the proven local matrices and dependency
metadata, but no numeric world slot is claimed.

## Boundary

Phase 550 closes **MultiMatrix arithmetic**, not the top-level root producer.
The next scene step is to trace the root matrix passed into the top-level
LOD/HIERARCHY `+0x2c` update and then join that proven world transform with
`SHIFT.SGBScenePlacement/1` and the Phase 548 OBJECT render handoff for
RenderBinding admission.
