# Phase 207 — headless Vulkan graphics pipeline

Phase 207 adds a real graphics pipeline on Linux using SPIR-V shaders.

The optional target:
- compiles GLSL vertex/fragment shaders with glslangValidator;
- creates Vulkan shader modules;
- creates a render pass, framebuffer and graphics pipeline;
- draws one triangle with vkCmdDraw;
- copies the rendered R8G8B8A8 image through host-visible staging memory;
- writes a P6 PPM checkpoint.

The target remains window-system independent.

This is still a backend smoke test, not a BMW render. No MEB/material semantics are introduced here. The next stage is translating the existing neutral RenderCommand vertex/index resources into Vulkan buffers and attributes.
