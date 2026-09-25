# Phase 235 — real DDS to Vulkan resource bridge

Phase 235 connects the existing retail-texture decoder to the native Vulkan packet
format without introducing a second decoder.

Flow:

`DDS bytes → texture_reference.decode_dds() → ReferenceTexture/1 or ReferenceCubeTexture/1 → VulkanTexturePacket/1 / VulkanCubeTexturePacket/1`

The bridge records:
- source DDS SHA-256;
- decoded base-level pixel SHA-256;
- source dimensions and source compression format;
- packet paths and versions;
- deterministic provenance in `dds_sources.json`.

Current sampler boundaries remain explicit:
- ordinary material textures use the D3D9 sampler register already present in RenderCommand;
- the proven BMW environment cube remains fixed to s3;
- unsupported/extra mappings fail closed.

This does not yet select real BMW DDS files from the retail BFF automatically. It provides
the deterministic bridge needed once a real material slice identifies those resources.
