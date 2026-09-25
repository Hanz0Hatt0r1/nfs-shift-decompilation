# Phase 222 — BMW material slice to Vulkan bundle

Phase 222 bridges the existing real BMW material-slice output into the Linux Vulkan
bundle without reparsing the game archives.

The adapter:
- accepts a material-slice JSON containing SHIFT.RenderCommand/1;
- locates the neutral mesh payload;
- requires the exact BMW M3 KIT00 body MEB identity;
- requires explicit Vulkan vertex/pixel shader sources;
- delegates packet generation to SHIFT.BMWVulkanBundle/1;
- records material-slice provenance in material_slice_source.json.

This closes the remaining manual conversion between the proven BMT/FX/FXO material
slice and the Vulkan backend. It does not fabricate missing shader/material/resource
evidence and does not claim a native render without the SPIR-V and runtime gates.
