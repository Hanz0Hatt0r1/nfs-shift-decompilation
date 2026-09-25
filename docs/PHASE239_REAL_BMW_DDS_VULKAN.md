# Phase 239 — real BMW material DDS to Vulkan integration

Phase 239 connects the real BMW material slice to the existing DDS-to-Vulkan packet bridge.

The material slice records each resolved DDS as compact provenance: archive name, exact resource path, source SHA-256 and decoded metadata. Retail bytes are not committed.

The Vulkan adapter accepts optional source BFF paths. For each selected material texture it requires an exact provenance path, exactly one supplied BFF with the recorded archive name, exactly one matching entry, and a SHA-256 match before extracting the DDS into an ephemeral directory.

The extracted DDS is passed through the existing `vulkan_dds_bridge.py`, so the final bundle receives the same `VulkanTexturePacket/1` and `VulkanCubeTexturePacket/1` formats already exercised by Linux Vulkan CI.

The environment cube remains explicit via `--environment-cube-dds`. No automatic `s3` selection is introduced. Shadow-map `s0` remains an external runtime dependency.

All failures are fail-closed. Ephemeral extraction paths are never written to persistent provenance.