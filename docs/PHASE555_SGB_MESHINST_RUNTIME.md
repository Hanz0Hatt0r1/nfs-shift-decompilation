# Phase 555 — SGB MeshInst runtime layout and loader split

Phase 555 follows the Phase 554 type-7 factory case into the concrete retail
`MeshInst` constructor and its shared `MeshType` loader path.

## Loader split

`FUN_0085aac0` is the `MeshType` base constructor used by both type 0 and
type 7 resources. For the MeshInst extensions proven in Phase 554 it dispatches:

| Extension | Loader | Retail debug/source name |
|---|---|---|
| `.imx` | `FUN_008587e0` | `CMeshPrimitiveType::LoadXMLMeshFromResource` |
| `.imb` | `FUN_00859800` | `CMeshPrimitiveType::LoadBinaryMeshFromResource` |

Both are identified by retail strings in
`.\Source\Platforms\Win\CPrimitiveType.cpp`.

The XML path exposes source-backed mesh concepts including `Vertices`,
`Streams`, `Buffers`, `EnvMapType`, `BOUNDSPHERE`, `AABBOX` and
`BONES`. This does not imply that the binary IMB grammar is already decoded.

## MeshInst runtime object

The type-7 factory allocates `0xb0` bytes and calls `FUN_0085ae20`.

The constructor:

1. calls the `MeshType` base constructor `FUN_0085aac0`;
2. installs vtable `PTR_FUN_00b1d480`;
3. copies source descriptor `+0x30` to runtime `+0x80`;
4. zeros runtime `+0x88..+0xac`;
5. when `+0x80 != 0`, allocates 16-byte-aligned storage sized
   `(+0x80) * 0x40` and stores the aligned pointer at `+0x84`;
6. registers the instance through
   `FUN_00834a60(DAT_00c26058, 10, this)`.

The project records the `+0x80` value as a count because it is directly used
as the multiplier for `0x40`-stride storage. It does not promote a more
specific per-element semantic without another consumer.

## Lifecycle

`FUN_0085af00` unregisters category 10 through
`FUN_008352f0(DAT_00c26058, 10, this)`, frees the aligned `+0x84` storage,
releases the observed `+0x20` and `+0x8c` resources through
`FUN_0082ea80`, then enters base cleanup `FUN_0085ac90`.

The machine-readable contract is `SHIFT.SGBMeshInstRuntime/1`.

## Scene integration

For type-7 OBJECT resources, `SGBObjectRenderHandoff` now embeds this runtime
contract. `SGBRenderBindingAdmission` preserves it and
`SGBRenderBindingBridge` distinguishes the remaining neutral adapter gap as:

- `meshinst-xml-adapter-unimplemented` for `.imx`;
- `meshinst-binary-adapter-unimplemented` for `.imb`.

Ready MEB objects continue through the existing generic RenderBinding path even
when another object in the same scene is blocked by one of these adapter gaps.

## CLI

```bash
python shift_importer.py sgb-meshinst-runtime \
  tracks/example/banner.imb out/meshinst-runtime.json

python shift_importer.py sgb-meshinst-runtime \
  tracks/example/banner.imb out/meshinst-runtime.json \
  --instance-count 12
```

The optional count represents an independently observed descriptor `+0x30`
value. It is not guessed from the filename or payload.

## Boundary

Phase 555 closes:

- MeshInst inheritance from MeshType at construction;
- IMX XML versus IMB binary loader selection;
- the 0xb0-byte runtime layout extension;
- `+0x80` count → `+0x84` aligned `0x40`-stride storage;
- renderer category-10 registration/unregistration;
- the observed teardown path.

Still open:

- serialized IMB binary grammar;
- a neutral IMX/IMB geometry/material adapter;
- the exact higher-level semantic of each 0x40-byte instance-storage element;
- independent MatrixNumber SceneGraph update-history blockers.

Evidence:
`evidence/sgb_meshinst_runtime_source.json`.
