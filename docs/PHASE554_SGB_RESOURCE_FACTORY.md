# Phase 554 — SGB OBJECT resource factory classification

Phase 554 closes the next source-backed boundary after the Phase 553
scene-to-RenderBinding bridge: the retail renderer does **not** treat the
serialized OBJECT resource string as an MEB path directly.

## Retail factory path

The binary OBJECT loader still stores its resource descriptor at wrapper
`+0x80`. At render time OBJECT vfunc `0x00699230` submits that descriptor
through renderer global `DAT_00c26058`, vfunc `+0x214`.

The `+0x214` entry reaches:

```text
FUN_00832a50
  -> FUN_00831940
```

The descriptor is constructed with type `0`. `FUN_00831940` then inspects
the resource filename extension before its factory switch.

Source-backed extension promotion:

| Extension | Descriptor type after promotion | Retail factory/cache name |
|---|---:|---|
| other | 0 | MeshType |
| `.imb` | 7 | MeshInst |
| `.imx` | 7 | MeshInst |

The extension comparisons use `FUN_0040f060` and the retail strings at
`DAT_00b18c98 = "imb"` and `DAT_00b18c94 = "imx"`.

## Factory cases

The observed switch cases used by this SGB path are:

- type 0: allocate `0x80` bytes and construct through `FUN_0085aac0`;
- type 7: allocate `0xb0` bytes and construct through `FUN_0085ae20`.

The retail resource-cache names for these cases are `MeshType` and
`MeshInst` respectively.

This classification is emitted as
`SHIFT.SGBObjectResourceFactory/1` and is carried through
`SGBObjectRenderHandoff` and `SGBRenderBindingAdmission`.

## Type-7 OBJECT render branch

After the renderer returns the render instance, OBJECT vfunc
`0x00699230` checks descriptor `+0x04`.

For type 7 only, it performs an additional render-instance vfunc `+0x04`
call with the observed flag/arguments before the common transform submission
through render-instance vfunc `+0x2c`.

Phase 554 preserves this branch explicitly instead of treating MeshInst as a
normal MeshType instance.

## Neutral IR boundary

The existing neutral render pipeline is MEB-based. Phase 553 therefore remains
valid as a **neutral MEB adapter**, but Phase 554 removes the implication that
the retail `MeshType` factory is synonymous with MEB.

The bridge now distinguishes three cases:

```text
scene-admitted resource
  -> retail factory classification
     -> .meb: existing neutral MEB -> BMT/FXO RenderBinding adapter
     -> type 0 non-MEB: MeshType adapter gap
     -> type 7 .imb/.imx: MeshInst adapter gap
```

No conversion from MeshType or MeshInst to MEB is invented.

## Importer correction

The generic resource classifier previously labelled `.imb` as
`ANIMATION`. Retail factory evidence contradicts that classification for this
resource path.

Phase 554 changes:

- `.imb` -> `MESH_INSTANCE`;
- `.imx` -> `MESH_INSTANCE`;
- dependency scanning now recognizes `.imx` references.

Historical parser/reference snapshots are not rewritten.

## Evidence

Machine-readable evidence is stored at:

`evidence/sgb_object_resource_factory_source.json`

Primary recovered functions:

- `0x00699230` — OBJECT render submission;
- `FUN_00836300 -> FUN_008362a0(..., 0)` — descriptor type initialization;
- `FUN_00832a50` — renderer factory vfunc entry;
- `FUN_00831940` — extension promotion and factory switch;
- `FUN_0085aac0` — MeshType construction;
- `FUN_0085ae20` — MeshInst construction.

The recovered source path for the factory code is
`.\Source\Platforms\Win\CPrimitiveType.cpp`.

## Remaining boundary

Phase 554 proves retail factory classification and the type-7 render branch.
It does not yet decode MeshType/MeshInst serialized payloads or map
`.imb/.imx` into the neutral geometry/material IR.

Independent scene blockers remain:

- concrete per-instance SceneGraph update history for unresolved MatrixNumber
  objects;
- MeshType non-MEB neutral adapter semantics;
- MeshInst `.imb/.imx` payload/instance semantics;
- higher-level streaming, LOD and visibility scheduling.
