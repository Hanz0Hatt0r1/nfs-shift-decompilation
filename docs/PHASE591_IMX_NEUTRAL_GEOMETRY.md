# Phase 591 — source-backed IMX XML neutral geometry

Phase 555 proved that MeshInst type 7 selects the retail XML loader
`FUN_008587e0` for `.imx` resources. Until Phase 591 the project recorded
that loader boundary but intentionally stopped before decoding the XML mesh.

Phase 591 reconstructs the source-backed XML grammar and connects it to the
same neutral geometry vocabulary already used by MEB and IMB.

## Retail loader evidence

The recovered function is:

`FUN_008587e0 = CMeshPrimitiveType::LoadXMLMeshFromResource`

from:

`.\Source\Platforms\Win\CPrimitiveType.cpp`.

The loader locates a `MESH` element and reads these exact root attributes:

- `Vertices`;
- `Streams`;
- `Buffers`;
- optional `EnvMapType`.

It then consumes:

- `BOUNDSPHERE Centre/Radius`;
- `AABBOX Min/Max`;
- optional `BONES NumBones` with `NODE Name/Transform`;
- repeated `STREAM Type/Usage/Channel` children;
- repeated `ITEM` rows under each stream;
- repeated `INDEXBUFFER` children;
- `INDEXBUFFER Material/Entries/NumBones/BoneIndices`;
- repeated `TRIANGLE Indices`.

The 12-float bone `Transform` field is expanded by the retail loader into a
row-major 4x4 matrix by inserting 0 at elements 3/7/11 and 1 at element 15.

## Exact Type table

The retail Type-name pointer table at `0x00b901d0` contains, in ordinal
order:

```text
0  F32
1  F32Vec2
2  F32Vec3
3  F32Vec4
4  RGBA32
5  U8Vec4
6  S16Vec2
7  S16Vec4
8  U8Vec4N
9  S16Vec2N
10 S16Vec4N
11 U16Vec2N
12 U16Vec4N
13 U10Vec3
14 U10Vec3N
15 F16Vec2
16 F16Vec4
```

The recovered XML ITEM conversion switch has explicit cases only for ordinals
0..5. Phase 591 therefore rejects XML streams using higher ordinals instead of
inventing conversion behavior.

For the supported XML cases the byte sizes are:

`4, 8, 12, 16, 4, 4`.

## Exact Usage table

The retail Usage-name pointer table at `0x00b901a8` contains:

```text
0 Position
1 BlendWeights
2 Normal
3 TexCoord
4 Tangent
5 Binormal
6 Colour
7 Depth
8 BlendIndices
```

The corresponding D3D9 usage codes recovered through `FUN_00853c40` are:

`0, 1, 3, 5, 6, 7, 10, 12, 2`.

The loader selects these ITEM attribute names by Usage ordinal:

```text
Position     -> Pos
BlendWeights -> Weights
Normal       -> Normal
TexCoord     -> UV
Tangent      -> Tangent
Binormal     -> Binormal
Colour       -> Colour
Depth        -> Depth
BlendIndices -> Indices
```

`Channel` is copied directly to the D3D9 UsageIndex byte.

## Neutral property identity

Phase 591 uses the same source-backed
`[Type ordinal, Usage ordinal, Channel]` property identity already proven by
the binary MeshInst path.

Examples:

- `F32Vec3 + Position + 0 → 200`;
- `F32Vec3 + Normal + 0 → 220`;
- `F32Vec2 + TexCoord + 0 → 130`;
- `F32Vec4 + BlendWeights + 0 → 310`;
- `RGBA32 + Colour + 0 → 460`;
- `U8Vec4 + BlendIndices + 0 → 580`.

Only established neutral fields are promoted. Other successfully decoded XML
streams remain in `deferred_streams`.

`RGBA32` is parsed as the retail base-0 integer and preserved as its exact
four little-endian D3DCOLOR bytes; no new RGBA/BGRA semantic claim is added.

## Index buffers

The XML loader writes primitive type 4 for every `INDEXBUFFER`.

`FUN_00853c80(Entries, 4)` proves:

`index_count = Entries * 3`.

Each `TRIANGLE Indices` contributes exactly three unsigned 16-bit indices.

Phase 591 validates:

- declared `Buffers` count;
- `Entries` versus actual TRIANGLE count;
- three indices per TRIANGLE;
- vertex-range validity;
- optional NumBones/BoneIndices palette count.

## Contract

The adapter is:

`src/scene/imx_neutral_geometry.py`

and emits:

`SHIFT.IMXNeutralGeometry/1`.

Its nested mesh uses:

`SHIFT.NeutralMesh/1`.

This is a shared renderer vocabulary only. The contract explicitly does not
claim IMX/MEB or IMX/IMB serialized-container equivalence.

## Scene/render integration

Phase 591 removes the previous
`meshinst-xml-adapter-unimplemented` blocker.

Admitted `.imx` resources now follow:

```text
SGB OBJECT
  -> MeshInst/type 7
  -> FUN_008587e0-compatible XML parse
  -> SHIFT.IMXNeutralGeometry/1
  -> BMT/FX/FXO material path
  -> DrawPacket / StaticDraw / RenderCommand
```

The packet preserves:

- `source_kind = "IMX"`;
- `neutral_adapter_format = "SHIFT.IMXNeutralGeometry/1"`;
- IMX source path/archive/SHA from IR.

The neutral Vulkan draw-bundle helper also unwraps the IMX wrapper.

## Runtime-proof boundary

The Silverstone runtime shader admission chain in Phases 568–577 remains
specifically tied to exact IMB resource identity and is not reused for IMX.

Phase 591 adds source/static IMX geometry support. It does not claim runtime
same-instance proof for an IMX resource.

## Corpus boundary

No `.imx` resource names were found in the supplied Silverstone Era3,
Vehicles or SHIFT-tail BFF string tables used during this phase.

Therefore Phase 591 is source-validated and regression-tested, but it does not
claim production IMX corpus coverage.

## Next

With both MeshInst serialization branches now normalized, the remaining scene
work no longer includes an IMX adapter blocker. The autonomous next candidates
are:

- per-instance SceneGraph MatrixNumber update-history recovery;
- repeated-instance runtime draw disambiguation;
- remaining renderer-owned resource types;
- broader scene streaming/LOD semantics.

Authentic Silverstone D3D9 content remains an external evidence gate.
