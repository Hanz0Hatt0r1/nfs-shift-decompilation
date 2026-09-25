# Phase 217 — BMW Vulkan bundle SPIR-V gate

Phase 217 turns the shader portion of SHIFT.BMWVulkanBundle/1 into a machine-checkable
SPIR-V stage.

The compiler reads only shader sources already copied from the selected RenderCommand.
When glslangValidator is available, vertex and pixel stages are compiled to SPIR-V and
hashed. Compiler errors are hard blockers. When the validator is absent, the status is
explicitly unavailable rather than pretending the shader is native-ready.

The bundle metadata is also corrected so the selected RenderCommand's exact mesh
reference, vertex count and triangle count survive the RenderBinding selection step.

This still does not execute the real BMW shader on Vulkan; it proves the next build
boundary: RenderCommand shader source -> SPIR-V artifact.
