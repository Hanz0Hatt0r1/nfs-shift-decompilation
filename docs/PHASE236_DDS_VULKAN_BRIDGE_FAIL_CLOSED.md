# Phase 236 — fail-closed DDS to Vulkan resource bridge

Phase 236 hardens the real DDS -> Vulkan resource bridge after the first CI execution.

The bridge now treats decoder failures and packet-builder incompatibilities as explicit
blocking reasons instead of leaking ValueError/OSError to callers. A DDS resource that
was supplied to a material sampler but decodes to a cubemap is reported as a type
mismatch, not also as a missing 2D resource.

The successful path remains:
DDS -> decode_dds() -> ReferenceTexture/1 or ReferenceCubeTexture/1 ->
VulkanTexturePacket/1 / VulkanCubeTexturePacket/1.

No retail resource is auto-selected; source identity and decoded-pixel hashes remain
part of the provenance report.
