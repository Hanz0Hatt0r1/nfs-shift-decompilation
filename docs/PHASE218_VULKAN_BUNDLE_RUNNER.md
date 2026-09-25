# Phase 218 — native Vulkan BMW bundle execution boundary

Phase 218 introduces the native executable boundary for a prepared BMW Vulkan bundle.

The runner consumes only the bundle artifacts:
- geometry.svpk;
- constants.svcp;
- optional textures.svtp;
- optional environment_cube.svcp.

It intentionally does not parse BFF, MEB, BMT or RenderCommand JSON.

This phase stops before arbitrary bundle shader execution because a general native runner
needs SPIR-V reflection to derive exact descriptor/resource interfaces for mixed sampler2D
and samplerCube bindings. The existing individual Vulkan resource checkpoints remain the
validation path until that reflection layer is implemented.

This is a deliberate blocker, not a claimed render.
