# Phase 245 — lossless sampler ABI preservation

Phase 245 keeps the binary `SHIFT.VulkanTexturePacket/1` wire format unchanged while adding two JSON artifacts to every prepared Vulkan bundle:

- `sampler_contracts.json` — the normalized D3D9-FX sampler state for material textures and explicitly described external samplers;
- `sampler_contracts.meta.json` — the same contract cryptographically tied to the exact `textures.svtp` SHA-256.

The preserved state includes min/mag/mip filters, address U/V/W, anisotropy, LOD bias, and sRGB/linear color-space selection where supplied.

The current native executor still consumes only the existing four-way `sampler_mode` field from `SVTP/1`; the sidecar explicitly reports `preserved-not-consumed` rather than claiming sampler parity. Missing runtime state such as the shadow-map `s0` remains explicit rather than synthesized.
