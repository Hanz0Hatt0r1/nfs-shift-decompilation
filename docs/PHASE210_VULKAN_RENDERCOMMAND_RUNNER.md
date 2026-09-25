# Phase 210 — Linux Vulkan RenderCommand runner

Phase 210 removes the last manual handoff between the Python neutral renderer and the
native Vulkan geometry backend.

vulkan_render_command.py:
1. reads SHIFT.RenderBinding/1;
2. selects one RenderCommand/1 and submesh;
3. creates the versioned VulkanGeometryPacket/1;
4. fingerprints the packet;
5. optionally launches shift_vulkan_render_geometry;
6. hashes the resulting PPM.

prepare-only mode is available on machines without Vulkan. Native execution is
reported as blocked when the executable is missing; the runner never treats a
prepared packet as a rendered image.

The native process still consumes only the binary packet and does not parse BFF/MEB.
