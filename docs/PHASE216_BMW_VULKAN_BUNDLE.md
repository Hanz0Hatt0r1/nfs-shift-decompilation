# Phase 216 — BMW Vulkan bundle

Phase 216 packages one exact BMW RenderCommand submesh for the Linux Vulkan backend.

The bundle contains versioned native handoffs for geometry and D3D9 float constants, optional material 2D textures, optional environment cube, and copied Vulkan-target shader source from RenderCommand/1. It also records hashes, the exact M3 KIT00 body MEB reference, external sampler requirements and native execution status.

The bundle is deliberately preparation-only. It does not claim that the generated shader sources have compiled to SPIR-V or that a real BMW image has rendered. The current native smoke shaders remain separate checkpoints. Missing material textures or the required s3 environment cube are explicit blockers.
