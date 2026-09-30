# Phase 548 — SGB OBJECT render handoff

Phase 548 closes the source-backed boundary between a decoded binary SGB
`OBJECT` and the runtime render instance that consumes it.

The key retail method is OBJECT vfunc `0x00699230`.

## Resource path

The binary loader `FUN_0069a6c0` resolves the OBJECT third SGB-relative string,
creates the runtime resource descriptor and stores it at OBJECT wrapper
`+0x80`.

At render admission, vfunc `0x00699230` passes that descriptor to the renderer
global `DAT_00c26058` through renderer vfunc `+0x214`. The returned render
instance receives its transform through its own vfunc `+0x2c`.

This proves the resource-string → runtime-resource-descriptor → render-instance
handoff without naming an unproven higher-level renderer class.

## Transform selector

OBJECT wrapper `+0x84` is the source-backed `MatrixNumber`.

### MatrixNumber >= 0

The OBJECT registers itself with the inherited MultiMatrix context through
`FUN_006b1820` and selects:

```text
matrix_ptr = context.matrix_array(+0x04) + MatrixNumber * 0x40
```

The selected 0x40-byte matrix pointer is passed to render-instance vfunc
`+0x2c`.

Phase 548 validates the corresponding parent LOD/HIERARCHY MATRIX record and
emits the exact slot selector, but it does not pretend that the runtime-updated
MultiMatrix value is already a numerically materialized world matrix.

The source path itself identifies `FUN_006b1820` as
`.\Source\RenderHierarchy\MultiMatrix.cpp`.

### MatrixNumber == -1

No parent slot is used. Vfunc `0x00699230` builds a matrix directly from the
OBJECT wrapper:

- quaternion WXYZ at `+0x88`;
- offset XYZ at `+0x98`;
- uniform scale at `+0xa4`.

`FUN_00445ec0` generates the 4x4 rotation matrix,
`FUN_0068c560` scales its 3x3 basis, and the translation is written at flat
matrix indices 12..14.

Phase 548 reproduces those exact operations and can therefore emit the numeric
matrix for this branch without a runtime capture.

## Recursive hierarchy handoff

LOD/HIERARCHY runtime construction creates or inherits a MultiMatrix context
and invokes child vfunc `+0x24`. Nested OBJECT handoffs are collected with
their immediate parent matrix table so `MatrixNumber` can be validated
fail-closed.

The aggregate contract is:

`SHIFT.SGBObjectRenderHandoffSet/1`.

## CLI

```bash
python shift_importer.py sgb-runtime track.sgb out/sgb-runtime.json
python shift_importer.py sgb-object-render-handoff \
  out/sgb-runtime.json out/object-render-handoff.json
```

## Boundary

Phase 548 proves resource admission and transform **selection**.

For parent-MultiMatrix objects the exact runtime world matrix remains dependent
on MultiMatrix hierarchy evaluation/update. Draw admission remains false until
that numeric context is joined to the Phase 547 placement contract.
