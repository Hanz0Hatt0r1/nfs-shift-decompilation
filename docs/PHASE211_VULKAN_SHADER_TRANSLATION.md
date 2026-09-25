# Phase 211 — Vulkan shader translation

Phase 211 makes the neutral D3D9 ShaderProgram capable of emitting Vulkan-targeted
GLSL 450 while preserving the existing GLSL ES 3.1 output.

The Vulkan target:
- uses GLSL 450 core syntax;
- preserves the D3D9 float c-register UBO at binding 14;
- keeps the same vertex-input/varying locations;
- keeps sampler bindings explicit;
- can be compiled and linked with glslangValidator using the Vulkan target.

SHIFT.LinkedShaderPair/1 now carries both GLSL ES and Vulkan GLSL stage sources.

No native Vulkan material draw is claimed by this phase. SPIR-V compilation is the
validation/build boundary; native descriptor sets and runtime constants are next.
