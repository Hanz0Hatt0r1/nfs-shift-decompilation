# Process 2 — captured D3D9 draw on Vulkan (2026-10-21)

## Result

`vulkan_d3d9_capture_bundle.py` extracts a supported `DrawIndexedPrimitive`
from the richer PortProton retail capture, translates its captured shader pair
and state, and writes the existing native bundle format. The native executor
now accepts SVGP v4 capture geometry, preserves 16-bit indices, applies the
captured base vertex and draw range, and uses the captured target and viewport.
It requests Vulkan 1.1 and keeps the bundle executor independent of XCB and
Wayland.

The validated call is event 5245407/frame 5868: a triangle list with 36
primitives, 38 vertices, and 108 indices on the captured 800×600 target. Its
VB, IB, declaration, shaders, texture, constants, sampler settings, viewport,
clear, surface formats, and relevant render states are recorded in
[`shift_d3d9_vulkan_capture_replay_20261021.json`](../evidence/shift_d3d9_vulkan_capture_replay_20261021.json).
The captured color format is D3DFMT_R32F (114), and the captured depth/stencil
format is D3DFMT_D24S8 (75); the executor uses `VK_FORMAT_R32_SFLOAT` and
`VK_FORMAT_D24_UNORM_S8_UINT` for those attachments. The format identifiers are
listed in [Microsoft's D3DFORMAT reference](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dformat).
The captured sampler has linear minification, magnification, and mip filtering.
Its DDS contains one mip level, so mip filtering has no level-selection effect.
Replay records that state and rejects active mip filtering on multi-level DDS
textures until the native packet and executor support mip chains.
The compiled vertex and pixel stages link successfully. The native submission
ran on both a GTX 950 and Mesa llvmpipe with Vulkan validation enabled and zero
validation errors on each device. The PPM preview maps the R32F channel to
grayscale for inspection; it is not a replacement for the uncaptured retail
target image.

## Translation fixes exercised by the capture

- D3D scalar source swizzles replicate to four lanes; masked writes apply the
  destination mask to the right-hand value.
- Immediate `DEF` constants are embedded in translated GLSL.
- A declared vertex `POSITION` output writes `gl_Position`.
- Vertex and pixel constant blocks use distinct instances and Vulkan bindings
  14 and 15.
- Captured `D3DCULL_CW`/`D3DCULL_CCW` values map against the renderer's CCW
  Vulkan front face. The D3D9 downward viewport uses a negative Vulkan
  viewport height, available in core Vulkan 1.1.
- Captured `D3DSAMP_MIPFILTER` is preserved; active mip filtering on a
  multi-level texture fails closed because the native executor uploads one mip.

These are translation and command-submission results, not a comparison against
the original frame. The proxy emits buffer payload events from successful
Lock/Unlock writes, but this capture contains only full-buffer snapshots, not
an ordered set of partial ranges establishing every byte version at each draw.
The Vulkan bundle now reconstructs draw-local bytes only from ordered ranges
with complete coverage; older full snapshots remain generation snapshots, not
proven draw-local bytes. This capture also has no original render-target image.
The evidence is explicitly marked `retail_image_parity_proven: false`.

The separate audited first DIP, event 1110/frame 344, still has no VB/IB
payloads or texture snapshots and is not submitted by this change. This
capture replay does not integrate with Process 1's runtime, scheduler, or
startup path.

## Portability boundary

The geometry packet uses fixed-width little-endian fields and contains no
host-pointer data. The replay path uses Vulkan 1.1 core commands and no
window-system surface API, so its renderer-side format does not depend on XCB
or Wayland. The Linux build and replay ran on x86-64. ARM64/Android was not
cross-built because no Android NDK is installed on this host; Android runtime
parity is not claimed.

## Verification

- 75 focused Python tests passed across shader translation, D3D9/Vulkan state,
  draw packets, native bundle contracts, and Linux/Android surface contracts.
- Every `native_vulkan` CMake target built successfully.
- `tools/run_linux_vulkan_smoke.py` completed its material bundle and two-draw
  bundle-set preparation on the host GPU and llvmpipe; native validation
  reported zero errors.
- The captured event 5245407 bundle compiled both shader stages, linked them,
  and completed native Vulkan validation with zero errors.
- The sampler regression suite passed 9 tests; event 5245407 was rebuilt from
  its retail capture and executed on the GTX 950 with validation enabled and
  zero errors.
