# Phase 412 — Raw SDF solver capture ingestion

The project now has an explicit-offset binary reader for captured SDF solver state.

## Input contract

The reader accepts a raw byte blob plus:

- `scalar_count`;
- `rhs_offset` in bytes;
- `matrix_offset` in bytes;
- optional row-index and runtime identity-node lists.

RHS is decoded as `scalar_count` little-endian IEEE-754 binary64 values. The matrix is decoded as a contiguous row-major `scalar_count × scalar_count` double array.

No memory address is inferred from the blob itself. A caller must supply the offsets from capture evidence.

## CLI

`tools/extract_sdf_solver_capture.py` writes the normalized `SHIFT.SDFSolverCaptureRuntime/1` JSON consumed by the Phase 411 comparator.

Example:

```bash
python tools/extract_sdf_solver_capture.py dump.bin solver.json \
  --scalar-count 40 \
  --rhs-offset 0x4000 \
  --matrix-offset 0x5000
```

The example offsets are illustrative only; the tool never assumes them.

## Validation boundary

The binary reader fails closed on negative offsets, truncated RHS/matrix regions and schema shape violations. It does not claim that an arbitrary blob is a retail solver frame until offsets and provenance are established.

No proprietary capture binary is committed by this phase.