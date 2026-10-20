# Process 2 — D3D9 Vulkan draw parameters (2026-10-21)

## Captured requirement

The audited SHIFT capture's first `DrawIndexedPrimitive` is event 1110/frame
344. It is `D3DPT_TRIANGLELIST` with 2 primitives, 4 vertices, `start_index=0`,
`base_vertex_index=0`, and a 12-byte `D3DFMT_INDEX16` index buffer. It maps to a
Vulkan triangle-list draw with 6 UINT16 indices.

The 1,581 selected race-target draws in the same audited capture also all use
triangle lists and INDEX16. The selected draw at event 1474620 has 538
primitives and a 3,228-byte index buffer, yielding 1,614 indices. Exact captured
inputs and expected parameters are in
[`shift_d3d9_vulkan_draw_parameters_20261021.json`](../evidence/shift_d3d9_vulkan_draw_parameters_20261021.json).

## Renderer change

`vulkan_d3d9_draw.py` maps the captured primitive count, start index, signed
base vertex, and INDEX16 format to Vulkan indexed-draw parameters. It checks
the requested index range against the captured buffer length and fails closed
on unobserved topology or index formats. It uses core Vulkan draw fields only;
the parameter mapping is valid for Vulkan 1.1 and has no host-pointer-width
assumptions.

This module is renderer-side translation evidence, not a Process 1 runtime
handoff contract. Its result explicitly remains ineligible for submission.

## Boundary

The audited base capture has no VB/IB payload events, texture snapshots, or
portable resource path+SHA pairs for these exact draws. This change therefore
does not submit an original SHIFT draw and proves no retail image parity. The
next native submission step needs exact bound resource bytes, shader modules,
render state, target, and a separately integrated runtime handoff. The
parameter contract is platform-neutral; ARM64/Android native integration has
not been run.

## Verification

- 42 targeted Python tests passed, including both captured-call regressions and
  existing D3D9/Vulkan draw, packet, and state tests.
- All `native_vulkan` targets built with CMake.
- The mixed-resource Linux Vulkan CI smoke ran on llvmpipe with
  `VK_LAYER_KHRONOS_validation` enabled and zero validation errors. It uses
  synthetic bundle inputs and validates backend health only; it does not
  consume the captured calls above.
