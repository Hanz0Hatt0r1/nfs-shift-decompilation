# Phase 206 — headless Vulkan image submission

Phase 206 proves the first native Vulkan GPU submission boundary on Linux without
requiring a window system.

The checkpoint creates:
- a Vulkan instance/device;
- a graphics queue and command pool;
- an offscreen R8G8B8A8 image;
- a host-visible staging buffer;
- an image layout transition;
- vkCmdClearColorImage;
- an image-to-buffer transfer;
- a host-side PPM artifact.

The result is machine-readable as SHIFT.VulkanHeadlessImage/1.

This is deliberately not a triangle or shader checkpoint. Shader/SPIR-V execution is
the next renderer stage. The software reference renderer remains the expected oracle
for later RenderCommand parity.
