# Phase 241 — material-slice to native Vulkan smoke

The Linux Vulkan smoke now enters through `build_bmw_vulkan_from_material_slice()` instead of calling the lower-level bundle builder directly.

The synthetic render command still exercises:
- vertex c-register bank 14;
- fragment/pixel c-register bank 15;
- sampler2D s1;
- samplerCube s3;
- indexed triangle geometry;
- the complete SPIR-V/interface/native Vulkan path.

The exact BFF DDS extraction path remains separately covered by the Phase 239/240 adapter regressions. This CI smoke uses deterministic inline `ReferenceTexture/1` and `ReferenceCubeTexture/1` resources so it can run without retail archives.
