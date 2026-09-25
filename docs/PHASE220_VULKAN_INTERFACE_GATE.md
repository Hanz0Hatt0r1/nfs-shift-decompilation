# Phase 220 — Vulkan bundle interface gate

Phase 220 compares the reflected SPIR-V descriptor contract with resources actually
present in a BMW Vulkan bundle.

The gate requires:
- set 0 uniform buffers only at bindings 14/15;
- set 1 sampler2D bindings to have matching 2D texture packets;
- set 1 samplerCube bindings to have matching cube packets;
- unsupported descriptor sets/types are hard blockers.

Extra uploaded resources are allowed because a RenderCommand can preserve resource
state that a selected shader permutation does not consume.

This is the validation boundary immediately before native Vulkan pipeline creation. It
does not execute a draw itself.
