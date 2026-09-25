# Phase 209 — Vulkan VertexLayout attribute packing

Phase 209 extends SHIFT.VulkanGeometryPacket/1 to version 2 and carries all vertex
attributes whose RenderCommand ABI is proven or otherwise explicitly supported by the
neutral mesh representation.

Supported native formats:
- FLOAT32x2 -> VK_FORMAT_R32G32_SFLOAT
- FLOAT32x3 -> VK_FORMAT_R32G32B32_SFLOAT
- FLOAT32x4 -> VK_FORMAT_R32G32B32A32_SFLOAT
- normalized U8x4 -> VK_FORMAT_R8G8B8A8_UNORM
- integer U8x4 -> VK_FORMAT_R8G8B8A8_UINT

COLOR0 uses the executable-backed D3DCOLOR evidence: its source byte order is treated
as BGRA and explicitly repacked to RGBA before the Vulkan normalized vertex fetch.

COLOR1 remains deferred while its declaration ABI is not proven.

The native Vulkan shader still consumes POSITION0 only. All additional supported
attributes are nevertheless present in the vertex binding description so the backend
layout is exercised before shader-material execution is enabled.

Version 1 packets remain readable: the native backend translates the old FLOAT3 format
code into the version-2 internal code before validation.
