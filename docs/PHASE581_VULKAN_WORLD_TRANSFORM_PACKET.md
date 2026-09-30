# Phase 581 — Vulkan world-transform packet

Phase 580 can reconstruct exact runtime-proven scene draws and build ordered
Vulkan child bundles, but the SGB world matrix still exists only as JSON
metadata.

Phase 581 freezes that transform into an explicit native ABI without guessing a
retail shader constant register.

## Contract

The new packet is:

`SHIFT.VulkanWorldTransformPacket/1`

with binary magic:

`SVWT`.

Implemented in:

`src/render/vulkan/vulkan_world_transform_packet.py`.

Binary layout:

- 16-byte header;
- 64-byte 4x4 float matrix payload.

The packet is deliberately separate from:

- `SHIFT.VulkanGeometryPacket/1`;
- retail material constant packets;
- any inferred shader register assignment.

## Matrix convention

SHIFT's scene matrices are source-backed as:

- row-major 4x4 storage;
- D3D row-vector convention;
- `p_world = p_object * world`.

GLSL's default `mat4` interpretation is column-major.

Uploading the same 16 float bytes to a GLSL `mat4` therefore presents the
numeric transpose of the D3D matrix, which is exactly the column-vector
equivalent:

`p_world_column = mat4(packet_bytes) * p_object_column`.

This means the packet does not need a lossy or ambiguous transpose step.

The translation remains the source row-major values:

- indices 12, 13, 14.

## Validation

The packet builder requires:

- exactly 16 numeric finite scalars;
- affine D3D row-vector form;
- source last column `[0, 0, 0, 1]`.

Nested 4x4 JSON matrices are accepted and normalized to the same 16-float
source order.

## Native checkpoint

`native_vulkan/src/vulkan_world_transform_check.cpp` parses the binary packet
independently in C++.

It verifies:

- magic/version;
- convention tag;
- exact matrix payload size;
- finite values;
- affine row-vector shape.

The checkpoint then transforms the reference point:

`[1, 2, 3, 1]`

using D3D row-vector multiplication.

The Linux Vulkan workflow creates a translation matrix
`[10, 20, 30]` and asserts the native result:

`[11, 22, 33, 1]`.

This proves Python serialization and native interpretation agree before the
matrix is connected to a material shader path.

## VulkanDrawBundle integration

A neutral Phase 579 bundle with a non-null world matrix now emits:

`world_transform.svwt`.

The bundle manifest records:

- packet format;
- relative path;
- SHA-256;
- translation;
- `scene_world_transform_serialized = true`.

The execution state becomes:

`packet-emitted-not-executed`.

This distinction is intentional.

Phase 581 proves the native transport ABI, not the retail shader constant
binding.

## NativeSceneVulkanSet integration

Each Phase 580 child entry now preserves the emitted world-transform artifact
and marks:

`world_transform_serialized = true`.

The ordered scene set still keeps:

`world_transform_executed = false`.

Therefore native scene submission remains blocked until the material Vulkan path
actually consumes SVWT or an equivalent proven transform channel.

## CLI

The root importer exposes:

```bash
python shift_importer.py vulkan-world-transform-packet \
  render-command.json \
  world_transform.svwt
```

The input may be any JSON object containing `world_matrix`.

## What Phase 581 does not claim

It does not:

- choose a retail vertex constant register;
- patch retail shader semantics;
- bake scene transforms into geometry;
- execute camera/view/projection;
- claim a correct Silverstone native frame.

Those remain separate evidence/runtime steps.

## Next

Consume `world_transform.svwt` in the native material draw path through a
dedicated, non-retail transform channel.

The safest next implementation is a native-side transform descriptor/push
constant path that is explicitly separate from reconstructed D3D9 material
constant registers, so existing retail constant provenance remains untouched.

Once the material executor consumes that channel, Phase 580 can clear the
`scene-world-transform-not-executed` blocker and move toward actual native
scene submission.
