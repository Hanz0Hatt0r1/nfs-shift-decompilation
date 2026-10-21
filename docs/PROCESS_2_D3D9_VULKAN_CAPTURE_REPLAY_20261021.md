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

## Latest live-race draw

A second capture was taken from a live race through the isolated `SHIFT_PROBE`
prefix and its `proc2` save. The raw 41,309,728-byte JSONL stays outside Git;
its SHA-256 and the exact retail executable hash are pinned in
[`shift_d3d9_vulkan_live_draw_proc2_20261021.json`](../evidence/shift_d3d9_vulkan_live_draw_proc2_20261021.json).
The capture retained three frames (12613–12615); the manual trigger fired on
12615 while the game was paused, so it contains no post-trigger frames.

Captured event 13647233/frame 12613 is an original triangle-list
`DrawIndexedPrimitive`: 97 vertices, 102 primitives, 306 INDEX16 indices, and
default stream frequencies for streams 0 and 1. Full-buffer VB and IB payloads
were recorded at frame 11849, before the draw at frame 12613; the capture has
no later payload update for either buffer. The captured VS/PS
pair compiles and links to SPIR-V. The draw targets an 800×600 D3DFMT_R32F
surface with D3DFMT_D24S8 depth; its pixel shader has no active samplers, so
the bundle correctly omits `textures.svtp`. `shift_vulkan_bundle_execute`
submitted the captured draw on a GTX 950 with Vulkan validation enabled and
zero errors.

This captured live-race draw completed native Vulkan submission. It is one
draw after the captured clear, not a reconstruction of the surrounding frame.
The PPM is diagnostic output and
does not establish retail image parity. The selected R32F shader writes a
single-channel value, which further limits visual comparison.

## First focused retail draw submitted through Vulkan

The live-race capture's first draw (event 13640309/frame 12613) uses shader
pair `vs:1af4a5f282f4b9fb` / `ps:da32197956d1cb89`, whose pixel shader contains
`IF b0`. The translator now emits valid parenthesized GLSL; both shader stages
compile and link. That older race capture still lacks the draw's DXT1 `s0`
snapshot, so event 13640309 itself remains blocked.

A fresh focused capture of the same retail shader pair records its first
`DrawIndexedPrimitive` as event 7435/frame 536: a triangle list with 4 vertices,
2 primitives, and 6 INDEX16 indices. The proxy queries all 16 vertex and pixel
boolean constants immediately before each successful draw. The target draw reads `b0=true`;
subsequent draws in the same capture read `false`, then `true`, proving this is
draw-local state rather than a shader-wide constant. The capture's queried
values now flow into the generated GLSL before the shader executes.

Its actual target resources and state are sufficient to build the native bundle:

- The vertex and index payloads cover their draw ranges and are recorded in
  the capture with partial Lock-range tracking enabled.
- The active `s0` is a 1024×256 managed D3DFMT_A8R8G8B8 texture. The capture
  proxy now snapshots lockable managed A8R8G8B8/X8R8G8B8 levels directly into
  uncompressed DDS, preserving row bytes and mip levels without a GPU
  `StretchRect` readback. Vulkan's existing DDS decoder verifies this snapshot.
- Captured sampler state uses linear filtering, `CLAMP_TO_BORDER` on U/V,
  transparent-black border color, and D3D9 sRGB texture sampling. `SVTP/1`
  retains its existing record layout; sampler modes 5–6 add transparent-black
  border modes, and adding 8 selects sRGB. Other border colors still fail
  closed.
- Separate alpha blending is enabled with captured ONE / ONE_MINUS_SRC_ALPHA
  factors and ADD operation; these are passed independently from the color
  blend factors into the Vulkan pipeline.

The bundle builder validates and links both SPIR-V shader stages, and
`shift_vulkan_bundle_execute --validation` submits this captured draw on a GTX
950 with Vulkan validation enabled and zero errors. Three executions of the
same bundle produced identical PPM hashes; before `b0` was initialized, repeat
executions produced different pixel data. The executor reports the captured
800×600 D3DFMT_A8R8G8B8 / D3DFMT_D24S8 target pair. Exact hashes and draw-local
state are in
[`shift_d3d9_vulkan_first_focused_draw_20261021.json`](../evidence/shift_d3d9_vulkan_first_focused_draw_20261021.json).

This proves one retail D3D9 draw can be translated, packaged, and submitted by
the Vulkan executor with its actual draw-local `b0` value. It does not compare
the result with the original frame, replay the surrounding frame, or connect
Process 1's guest runtime to the renderer. The older event 13640309 still needs
its original DXT1 snapshot; the new capture is a separate draw using the same
shader pair. The temporary PortProton capture profile was restored and the
retail executable hash remained unchanged.

The new capture contract records `SetStreamSourceFreq` state with each indexed
draw. Microsoft defines indexed-data and instance-data settings through
[`SetStreamSourceFreq`](https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-setstreamsourcefreq).
The replay builder resolves shader inputs across captured source streams,
assembles only the draw's byte ranges from ordered partial payloads, applies
discard invalidation, and flattens a captured single instance into the vertex
packet. It rejects missing frequency evidence, uncovered byte ranges,
ambiguous same-frame deferred writes, and multi-instance draws. A null
`SetDepthStencilSurface` binding is treated as no depth surface. Pixel shaders
with no sampled textures no longer require an empty texture packet; textured
draws still require captured snapshots for every active sampler.

## Translation fixes exercised by the capture

- D3D scalar source swizzles replicate to four lanes; masked writes apply the
  destination mask to the right-hand value.
- Immediate `DEF` constants are embedded in translated GLSL.
- `DEFB` definitions remain shader-local, while external `b#` values come
  from successful draw-local D3D9 constant queries. The bundle builder rejects
  a shader with an external bool register when that query is absent.
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

- This focused change passed 263 shader, D3D9 capture, texture, and Vulkan
  regressions; the MinGW x86 capture proxy and all native Vulkan CMake targets
  built successfully.
- `tools/run_linux_vulkan_smoke.py` rendered its material bundle and prepared
  its two-draw bundle set. The first focused SHIFT draw also passed native
  Vulkan validation on the GTX 950 with zero errors.
- 75 focused Python tests passed across shader translation, D3D9/Vulkan state,
  draw packets, native bundle contracts, and Linux/Android surface contracts.
- Every `native_vulkan` CMake target built successfully.
- `tools/run_linux_vulkan_smoke.py` completed its material bundle and two-draw
  bundle-set preparation on the host GPU and llvmpipe; native validation
  reported zero errors.
- The captured event 5245407 bundle compiled both shader stages, linked them,
  and completed native Vulkan validation with zero errors.
- The first focused draw using the repaired retail shader pair was packaged
  with its real texture, draw-local bool state, and other captured state, then
  submitted three times on a GTX 950 with validation enabled and zero errors;
  all three output PPM hashes matched. The earlier live-race event 13640309
  remains blocked on its missing DXT1 snapshot.
- The sampler regression suite passed 9 tests; event 5245407 was rebuilt from
  its retail capture and executed on the GTX 950 with validation enabled and
  zero errors.
- The follow-up stream-frequency, multi-stream, draw-local partial-range,
  null-depth, and untextured-shader regressions passed with the D3D9 capture
  and Vulkan shader suites: 113 passed.
- The complete repository test suite passed: 7,631 passed, 3 skipped. It used
  the exact `revenginstr` commit pinned by CI and the declared development
  dependencies.
- Every `native_vulkan` CMake target built. The native smoke script completed
  its two-draw material bundle-set path with validation enabled. The new live
  SHIFT draw also completed native submission with zero Vulkan validation
  errors on the GTX 950.
