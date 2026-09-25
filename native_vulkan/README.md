# Linux Vulkan bootstrap

This directory is the first native backend step for the SHIFT renderer.

The target architecture is:

```text
BFF -> IR -> DrawBinding -> RenderCommand/1
                         |
                         v
                Vulkan submission layer
                         |
              +----------+----------+
              |                     |
           SPIR-V                resources
        VS / PS stages       buffers / images
              |                     |
              +----------+----------+
                         v
                    Vulkan device
```

The existing Python desktop reference renderer remains the deterministic oracle. The
Vulkan backend must consume the same `SHIFT.RenderCommand/1` data rather than creating
a second interpretation of MEB/BMT/FXO semantics.

## Bootstrap build

On Linux:

    cmake -S native_vulkan -B native_vulkan/build
    cmake --build native_vulkan/build --config Release
    ./native_vulkan/build/shift_vulkan_probe

The probe has no window-system dependency. It only verifies that the Vulkan loader can
create an instance, enumerate physical devices and find a graphics or compute queue.

If the Vulkan SDK is unavailable, CMake reports that condition and does not create the
probe target. This keeps the repository's non-Vulkan parsing tests independent of a
machine-specific graphics stack.

## Backend rules

1. `RenderCommand/1` remains the source contract.
2. Shader translation targets SPIR-V; GLSL is retained as a validation/debug representation.
3. MEB interleaving/repack decisions stay in the neutral renderer layer.
4. Vulkan resource creation must use explicit descriptor/buffer/image contracts.
5. No undocumented game semantics are inferred by the Vulkan backend.


## Headless image checkpoint

After the bootstrap probe, the native backend can execute a real Vulkan transfer-only
image checkpoint without a window system:

    cmake -S native_vulkan -B native_vulkan/build
    cmake --build native_vulkan/build --config Release
    ./native_vulkan/build/shift_vulkan_headless_clear out/shift_vulkan_headless.ppm

The executable creates a Vulkan device and graphics queue, allocates an offscreen
R8G8B8A8 image, clears it through the Vulkan command buffer, copies it to a host-visible
staging buffer and writes a P6 PPM.

This phase intentionally has no shader or BMW semantics yet. It proves the native
offscreen resource/submission boundary that the later RenderCommand backend will use.

 
## RenderCommand geometry bridge

Phase 208 adds SHIFT.VulkanGeometryPacket/1 as the first native handoff format.
Generate it with:

    python vulkan_geometry_packet.py render_command.json mesh.json out/mesh.svpk

Then render it with:

    ./native_vulkan/build/shift_vulkan_render_geometry       out/mesh.svpk       out/mesh.ppm       native_vulkan/build/shaders

The packet is generated from SHIFT.RenderCommand/1 and neutral mesh data. The
native Vulkan process does not parse BFF or MEB JSON.
