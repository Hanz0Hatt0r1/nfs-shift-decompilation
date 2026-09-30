# Phase 583 — semantic-aware SVGP v3 native geometry ABI

Phase 582 proves the first real material-path execution of the dedicated
`SHIFT.VulkanWorldTransformPacket/1` (`SVWT`) by applying pure translation
to the uniquely known POSITION0 stream.

General affine execution is intentionally blocked there because SVGP v2 carries
only Vulkan location/format/offset/stride. The native side cannot safely decide
which non-position attributes are NORMAL, TANGENT or TANGENT2.

Phase 583 removes that ABI limitation without changing the neutral
RenderCommand contract.

## Binary change

`SHIFT.VulkanGeometryPacket/1` keeps the same 44-byte packet header and moves
its binary packet version from 2 to 3.

The attribute record changes from 16 bytes:

```text
uint32 location
uint32 format
uint32 offset
uint32 stride
```

to 20 bytes:

```text
uint32 location
uint32 format
uint32 offset
uint32 stride
uint32 property_id
```

`property_id` is the existing numeric SHIFT vertex property identity already
carried by `SHIFT.VertexLayout/1`.

Examples used by the active renderer path include:

- 200 — POSITION;
- 220 — NORMAL;
- 240 — TANGENT;
- 250 — TANGENT2;
- 310 — BLENDWEIGHT;
- 460/461 — COLOR0/COLOR1;
- 580 — BLENDINDICES;
- numeric UV property IDs preserved by the recovered layout.

No new semantic mapping is invented in Phase 583. The binary packet simply
preserves the identifier already admitted by the neutral vertex ABI.

## Writer

`src/render/vulkan/vulkan_geometry_packet.py` now emits:

- SVGP binary version 3;
- a 20-byte attribute record;
- exact numeric `property_id` per emitted attribute.

The JSON report remains `SHIFT.VulkanGeometryPacket/1` and continues to list
the full source attribute rows.

## Native readers

Every current native SVGP consumer accepts v3:

- `native_vulkan/src/vulkan_render_geometry.cpp`;
- `native_vulkan/src/vulkan_bundle_runner.cpp`;
- `native_vulkan/src/vulkan_bundle_execute.cpp`;
- `native_runtime/src/shift_runtime.cpp`.

For v3 they require every attribute to carry a non-zero SHIFT property ID.

POSITION0 must be:

- Vulkan location 0;
- FLOAT3;
- SHIFT property 200.

This makes the semantic identity explicit rather than inferred from location
alone.

## Legacy v1/v2 compatibility

The new readers continue to accept the old 16-byte attribute table.

Because old packets do not contain property IDs, compatibility is deliberately
minimal and evidence-safe:

- location 0 is reconstructed as property 200 because that POSITION0
  convention was already required by the old packet ABI;
- every other legacy attribute receives property ID 0/unknown;
- no normal/tangent identity is guessed.

SVGP v1 also restores the original format-code compatibility rule:

- v1 format code 1 is remapped to the historical FLOAT3 POSITION encoding;
- v2/v3 format code 1 remains FLOAT2.

This fixes the previous native_runtime inconsistency where v1 was nominally
accepted but could fail its POSITION format check.

## Regression proof

Python binary tests verify:

- packet version 3;
- 20-byte attribute records;
- exact property IDs for POSITION, NORMAL, COLOR, BLENDWEIGHT and
  BLENDINDICES.

Source-contract tests cover every native reader.

The Linux Vulkan workflow additionally produces a real v3 BMW smoke bundle,
converts its geometry packet to legacy v2 by dropping property IDs, and runs
that legacy binary through:

1. the standalone Vulkan geometry checkpoint;
2. the native material bundle executor;
3. the XCB/Vulkan native runtime.

This proves the v3 upgrade does not invalidate prepared legacy v2 geometry.

## Boundary after Phase 583

Phase 583 does not itself execute rotation, scale, shear or reflection.

It makes that next step safe: the native material executor can now identify
POSITION 200, NORMAL 220, TANGENT 240 and TANGENT2 250 directly from the binary
geometry packet.

The next phase should extend SVWT execution to general non-singular affine
matrices:

- affine transform for POSITION;
- inverse-transpose 3x3 for NORMAL;
- linear 3x3 plus normalization for TANGENT/TANGENT2;
- unchanged UV/color/skinning fields;
- fail-closed handling for unsupported/missing semantic bases.

That transform can remain separate from all reconstructed retail D3D9 material
constant registers.
