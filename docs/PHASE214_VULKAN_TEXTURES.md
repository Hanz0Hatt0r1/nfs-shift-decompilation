# Phase 214 — Vulkan texture descriptors

Phase 214 establishes the resource path from RenderCommand sampler registers to actual
Vulkan sampled images.

The Python handoff is SHIFT.VulkanTexturePacket/1:
- one explicit texture record per D3D9 sampler register;
- RGBA8 base-level pixels;
- explicit sampler mode;
- source resource binding/texture/sampler identities;
- descriptor set 1.

The native Vulkan checkpoint:
- uploads RGBA8 pixels through a staging buffer;
- creates sampled images and image views;
- creates Vulkan samplers for the proven nearest/linear repeat/clamp subset;
- creates combined-image-sampler descriptors at the original sampler registers;
- executes a texture sampling shader;
- reads back an offscreen PPM.

Vulkan shader emission now places sampled textures in descriptor set 1, leaving set 0
for the D3D9 VS/PS constant banks.

Phase 214 is a synthetic texture/material resource checkpoint. It does not yet ingest
the real BMW DDS into native Vulkan automatically; the next step is to feed the actual
BMW RenderCommand texture bindings and then add samplerCube/environment resources.
