# Phase 223 — Linux Vulkan CI smoke

Phase 223 makes Linux native Vulkan execution an automated repository checkpoint.

GitHub Actions installs Mesa's software Vulkan driver plus Vulkan development tools,
builds the native backend, runs the probe/clear/triangle checkpoints, then executes a
synthetic mixed-resource BMW-style bundle through:

RenderBinding → Vulkan bundle → SPIR-V compile → descriptor/resource gate →
native Vulkan → offscreen PPM.

The fixture exercises:
- VS c-register bank 14;
- PS c-register bank 15;
- sampler2D s1;
- samplerCube s3;
- Vulkan VertexLayout packet v2;
- indexed geometry.

This is backend integration coverage only. It is not a BMW visual-parity claim and does
not replace the real Windows D3D9 same-instance capture gate.
