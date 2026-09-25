# Phase 212 — Vulkan stage-specific D3D9 constant ABI

SHIFT RenderCommand keeps vertex and pixel material constant usage separately. The
Vulkan backend now maps these banks to separate descriptor bindings:

- vertex c-register bank -> set 0, binding 14;
- pixel c-register bank -> set 0, binding 15;
- one c-register = 16 bytes;
- register range is bounded to 256 entries.

The mapping prevents the VS/PS constant banks from aliasing through a single Vulkan
descriptor.

ShaderProgram Vulkan emission now follows the same rule: vertex GLSL uses binding 14,
pixel GLSL uses binding 15. Existing GLES output remains unchanged.

The native geometry pipeline does not consume these constants yet. The next stage is
uploading RenderCommand constant_payload into these buffers and exposing the same
layout to material shaders.
