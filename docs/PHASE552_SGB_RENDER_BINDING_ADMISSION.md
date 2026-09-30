# Phase 552 — SGB placement → RenderBinding admission

Phase 552 joins the two source-backed scene contracts that previously ended at
separate boundaries:

```text
SHIFT.SGBScenePlacement/1
        +
SHIFT.SGBObjectRenderHandoffSet/1
        ↓
SHIFT.SGBRenderBindingAdmission/1
```

The output is deliberately a **scene-side admission** contract. It does not
pretend to be the existing generic `SHIFT.RenderBinding/1`, because that
contract additionally contains decoded MEB/BMT/FXO draw packets and commands.

## Identity join

The wrapper identity is already source-backed by Phases 545–548:

- `flat-summ` placement rows join to `SUMM` object handoffs by
  `source_record_index`;
- `part-node` placement rows join to `NODE` object handoffs by
  `source_record_index`;
- one wrapper may contain LOD/HIERARCHY and therefore expand to multiple
  recursive OBJECT handoffs. Each OBJECT path receives its own binding row.

This prevents resource-name guessing and preserves the exact wrapper/object
relationship.

## Admission gate

A binding is scene-ready only when all of these are proven:

- placement record is ready;
- spatial culling geometry is ready;
- OBJECT render handoff is ready;
- OBJECT resource reference is present;
- a numeric 4x4 world matrix is ready.

The last rule means MatrixNumber-backed objects with unknown SceneGraph update
history remain blocked, while explicit OBJECT transforms and runtime-proven
MultiMatrix transforms can be admitted independently.

Blocked rows do not erase ready rows. The report exposes admitted and blocked
counts so a capture can incrementally promote only the affected objects.

## Boundary

`draw_admission` remains false. Phase 552 only establishes that a concrete
scene object is eligible to enter the existing generic resource/render
pipeline. The next step is either:

1. recover/capture missing per-instance SceneGraph update history to promote
   blocked MatrixNumber rows; or
2. resolve already-admitted resource references through the existing
   MEB/BMT/FXO → `SHIFT.RenderBinding/1` pipeline.
