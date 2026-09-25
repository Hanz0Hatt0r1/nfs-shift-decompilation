# Phase 215 — Vulkan samplerCube / environmentMap

Phase 215 adds the native Vulkan resource type required by the BMW paint contract: environmentMap at D3D9 sampler register s3 with samplerCube semantics.

The handoff format is SHIFT.VulkanCubeTexturePacket/1. It requires a RenderCommand/1 with exactly one samplerCube external binding at s3, a complete SHIFT.ReferenceCubeTexture/1 with px/nx/py/ny/pz/nz faces, identical positive face dimensions, RGBA8 pixels, and explicit Clamp addressing with NEAREST/LINEAR filtering.

Native Vulkan creates a cube-compatible 2D image with six array layers, uploads the six faces with explicit layer indices, exposes VK_IMAGE_VIEW_TYPE_CUBE, creates a clamp sampler, binds the cube as a combined image sampler at descriptor set 1 / binding 3, executes a samplerCube shader and reads back the offscreen image.

The face order is explicit and fixed: px, nx, py, ny, pz, nz.

This remains a synthetic environment-map checkpoint. Real BMW s3 capture/content and exact cube orientation are still runtime evidence work.
