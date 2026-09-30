# Phase 589 — source-backed IMX neutral geometry

Phase 589 closes the remaining MeshInst XML adapter gap without treating IMX,
IMB or MEB as equivalent serialized formats.

The retail loader recovered from `SHIFT.exe.c` is:

`FUN_008587e0` —
`MWL::Renderer::WinRenderer::CMeshPrimitiveType::LoadXMLMeshFromResource`.

## Source grammar

The recovered loader consumes a `MESH` root with:

- `Vertices`, `Streams`, `Buffers`, optional `EnvMapType`;
- `BOUNDSPHERE Centre/Radius`;
- `AABBOX Min/Max`;
- optional `BONES NumBones` with `NODE Name/Transform`;
- `STREAM Type/Usage/Channel` with one `ITEM` per vertex;
- `INDEXBUFFER Material/Entries`, optional bone palette;
- `TRIANGLE Indices` as three uint16 indices.

The exact recovered enum/string tables are frozen in:

`evidence/imx_xml_mesh_loader_source.json`.

## Important usage distinction

IMX XML Usage values are mapped by the retail loader to D3D9 declaration usage
codes. They are not the binary IMB Usage ordinals used in serialized
Type/Usage/Channel triples.

For example:

- XML `Normal` maps to runtime usage 3 but neutral property `220`;
- XML `TexCoord` maps to runtime usage 5 but neutral property `130..134`;
- XML `Colour` maps to runtime usage 10 but neutral property `460/461`.

Phase 589 therefore maps XML streams by proven semantic/type identity. It never
constructs a neutral property ID by concatenating the XML runtime enum values.

## Neutral contract

New adapter:

`src/scene/imx_neutral_geometry.py`

emits:

`SHIFT.IMXNeutralGeometry/1`

over the shared:

`SHIFT.NeutralMesh/1`.

Promoted mappings are limited to already-established renderer semantics:

| XML Type / Usage | Neutral property |
|---|---|
| F32Vec3 Position | 200 |
| F32Vec3 Normal | 220 |
| F32Vec3 Tangent | 240 |
| F32Vec3 Binormal | 250 |
| F32Vec2 TexCoord channel 0..4 | 130..134 |
| F32Vec3 TexCoord channel 0..4 | 230..234 |
| F32Vec4 BlendWeights | 310 |
| RGBA32 Colour channel 0/1 | 460/461 |
| U8Vec4 BlendIndices | 580 |

The retail XML value-decode switch is recovered for source Type indices 0..5
(`F32` through `U8Vec4`). Later declaration types are recognized by the
source tables, but Phase 589 does not invent their XML value decode semantics:
their raw ITEM values are retained and render admission fails closed.

## Primitive normalization

Each `INDEXBUFFER` becomes one neutral primitive:

- material reference preserved exactly;
- primitive type fixed to source-backed triangle-list value 4;
- `Entries * 3` indices;
- optional uint16 bone palette;
- ordered `first_index/index_count`.

The XML loader does not serialize the binary IMB primitive range/bounds trailer.
Phase 589 therefore labels the per-primitive vertex range as derived from the
TRIANGLE indices and leaves primitive-local bounds unset. Mesh-level
`BOUNDSPHERE/AABBOX` remain source-backed.

## Render pipeline

`build_render_bindings_from_resource_instances()` now accepts:

- MEB;
- source-backed v0.4 IMB;
- source-backed IMX XML.

IMX packets record:

- `mesh.source_kind = "IMX"`;
- `mesh.neutral_adapter_format = "SHIFT.IMXNeutralGeometry/1"`;
- `vertex_layout.source = "IMX"`.

`SHIFT.SGBRenderBindingBridge/1` no longer emits
`meshinst-xml-adapter-unimplemented` for a valid IMX resource.

Runtime shader admission remains intentionally IMB-specific. Phase 589 does not
reuse `SHIFT.IMBRuntimeShaderAdmission/1` for IMX.

## CLI

```bash
python shift_importer.py imx-neutral-geometry \
  extracted_mesh.imx \
  out/imx-neutral.json
```

## Boundary

Phase 589 is source-backed and fail-closed. It does not claim:

- IMX/IMB/MEB container equivalence;
- unsupported XML stream value decoding;
- runtime shader attribution for IMX;
- production corpus coverage where no authentic IMX sample is available;
- higher-level MeshInst instance-storage semantics beyond the already-proven
  runtime layout.
