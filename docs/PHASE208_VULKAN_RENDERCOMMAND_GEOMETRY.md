# Phase 208 — RenderCommand to Vulkan geometry

Phase 208 connects the neutral renderer contract to the native Vulkan backend without
duplicating BFF/MEB parsing in C++.

## Boundary

Python consumes:
- SHIFT.RenderCommand/1;
- the neutral MEB mesh JSON.

It validates POSITION0 and materializes one selected triangle-list submesh into
SHIFT.VulkanGeometryPacket/1. The binary packet contains the interleaved position
buffer, uint32 indices and the normalization parameters required by the geometry
checkpoint.

C++ consumes only the packet. It:
- creates Vulkan vertex/index buffers;
- describes POSITION0 as VK_FORMAT_R32G32B32_SFLOAT;
- creates a depth-tested offscreen render target;
- submits vkCmdDrawIndexed;
- reads back the color image as PPM.

## Intentional Phase 208 limits

Only POSITION0 is submitted to Vulkan. Other RenderCommand vertex properties remain
reported as deferred. This is deliberate: the native backend must not invent MEB
packing or silently discard required shader inputs.

The material/shader blockers on RenderCommand do not make the packet exporter unusable
for the geometry-only checkpoint; the report preserves command_ready and the original
blockers for provenance.

## Next

Expand the binary packet to all proven vertex attributes, then bind the same
RenderCommand material/shader state. The reference renderer remains the output oracle.
