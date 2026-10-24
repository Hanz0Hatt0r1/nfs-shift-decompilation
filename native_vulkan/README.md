# Linux Vulkan backend

The native Vulkan backend consumes the neutral render contracts used by the desktop reference path.

Current retail-device output and Android ARM64 build status are tracked in
[`ANDROID_RENDER_STATUS_20261024.md`](ANDROID_RENDER_STATUS_20261024.md).
The Linux retail loading frame after relative constant addressing, Xenos gamma
conversion, and Copy/Convert channel fixes is recorded in
[`process2_linux_retail_loading_frame10_20261024.json`](../evidence/process2_linux_retail_loading_frame10_20261024.json).
That frame is not evidence of a visible menu or race scene. A Vulkan 1.1
4x-to-1x D24S8 `SAMPLE_ZERO` resolve/load path now has host and Redmi Note 8
Pro hardware regression coverage. The ReXGlue provider still needs to enable
`VK_KHR_create_renderpass2` and `VK_KHR_depth_stencil_resolve` for this path,
and report that capability to the plugin. Process 1 accepted this optional
contract; its provider wiring is pending. Until that lands, the plugin rejects
the mixed-sample path before submission. The resolve mode also needs comparison
against a subsequent retail frame. The latest full Android activity exits
before producing that frame.

## Implemented stages

- Vulkan instance/device/queue bootstrap;
- headless image/transfer checkpoint;
- RenderCommand geometry packet;
- vertex-layout packet;
- constant packet;
- texture/sampler packet;
- cubemap packet;
- SPIR-V reflection and interface gates;
- BMW material→DDS→Vulkan adapter;
- separately tested, bounded decoding of captured Xbox `PM4_DRAW_INDX` and
  DMA-source `PM4_DRAW_INDX_2` packets and vertex/texture fetch descriptors,
  plus normalization for captured index/vertex byte orders. The captured
  1024x256, format-6, tiled 2D texture
  can also be converted to linear texel order with its 8-in-32 byte swap. The
  run-054 1024x512, tiled format-19 DXT2/3 texture with 8-in-16 endian mode can
  also be untiled and expanded to RGBA8 without optional Vulkan BC support. The
  descriptor decoder maps the captured channel selectors, signs, X/Y/Z clamp
  modes, border code, filters, and anisotropy to semantic values; they are not
  yet applied to a Vulkan view or sampler. The captured black border code has
  unresolved alpha, so the backend does not guess a Vulkan border color. The
  captured color/depth target, viewport, and screen/window scissor are also
  decoded into a bounded neutral state contract. This does not map Xenos EDRAM
  tiles to Vulkan images or create a pipeline. A separate strict decoder now
  recognizes the live 1280x720 color Copy/Convert register tuple
  (`copy_control=0x00100000`, destination `0x0975e000`, format 6 with R/B swap).
  This is metadata only: the live mode-6 draw is still not submitted, and Xenos
  EDRAM accumulation/frontbuffer resolve remain unimplemented. The constants
  decoder resolves
  each stage's 256-register float window and the observed PS branch bools,
  including the VS a0-indexed c0-c3 window.
  A bounded decoder parses the captured VS/PS control-flow slots and their
  `vfetch_full`, `vfetch_mini`, and `tfetch2D` instructions, plus scheduled ALU operands,
  temporary-register addressing flags, scalar source selectors, and
  component-relative swizzles. The project-owned translator now emits Vulkan
  GLSL for the observed VS/PS pair, including its `b128`/`b129` branch path,
  vertex fetch, captured ALU subset, texture fetch/swizzle, and exports. It
  rejects unsupported control flow and operations. The actual captured pair
  compiled to Vulkan 1.1-compatible SPIR-V and passed `spirv-val`.
  `vfetch_mini` parsing has both a synthetic decoder regression and a live
  retail observation. The 108-byte VS uses a full fetch from constant 0 with
  format 57 and a seven-dword stride, followed by a format-38 mini fetch at
  dword offset 3. The project translator now applies the full fetch's inherited
  address, constant, and stride while retaining the mini's own format,
  destination, and offset. Its regression emits float3 and float4 inputs at
  byte offsets 0 and 12 with the observed 28-byte stride. Dynamic lookup now
  selects the captured fetch descriptor. The live point-list vertex shader
  also exercises the no-fetch path, which renders from `gl_VertexIndex` without
  a synthetic vertex buffer.
  The packet scanner frames contiguous big-endian type 0/1/2/3 PM4 packets and
  reports type-3 opcodes without applying state or executing commands. The
  project-owned `snapshot_guest_ring_batch` copies a committed dword-indexed
  ring interval, including wraparound, then frames its packets. The adjacent
  size helper bounds ReXGlue's `1 << (size_log2 + 3)` ring capacity before use.
  The PM4 type-0/type-1 decoder exposes raw register-write pairs. The live
  plugin applies the observed target/viewport/scissor registers and tracks the
  shader controls, required captured float constants, bools, and fetch
  descriptors. It also resolves captured `PM4_LOAD_ALU_CONSTANT` spans from
  guest memory. The captured three-dword `PM4_INDIRECT_BUFFER` form is
  decoded to a bounded guest address and dword length. The ring frontend can
  expand that form through a caller-supplied guest-memory reader, retaining
  packet source and nesting depth while rejecting short spans, cycles, and
  over-limit streams. The Linux ReXGlue plugin in
  `native_vulkan/rexglue_plugin` consumes the live ring and indirect buffers
  from `InitializeRingBuffer` / `CP_RB_WPTR` on an asynchronous worker. At each
  supported DMA-source `DRAW_INDX`/`DRAW_INDX_2` or AutoIndex `DRAW_INDX_2`,
  it checks the captured
  raster state, shader programs (including bounded inline `IM_LOAD_IMMEDIATE`
  code), constants, and descriptors; translates the bounded shader pair to
  project-owned GLSL; compiles Vulkan 1.1 SPIR-V; and resolves normalized
  index/vertex payloads plus the untiled texture. AutoIndex point lists with
  no vertex fetch and the captured AutoIndex rectangle-list form are supported
  when their raster state and Vulkan geometry-shader feature are available;
  unsupported captured target states still fail closed. At `PM4_XE_SWAP`, the
  plugin batches those draws and submits them into the ReXGlue presenter's output
  image through `shift_xbox_live_vulkan_renderer`. That renderer core has no
  XCB/Wayland dependency. The frame currently starts with a black clear and
  does not reconstruct prior Xenos EDRAM or import the guest frontbuffer as a
  completed image. Regressions cover PM4 draw/swap framing, ring wraparound,
  indirect buffers, and the plugin ABI. The Linux plugin/presenter smoke
  publishes a fixture ring through MMIO and verifies two prepared indexed
  draws reach Vulkan submission at `XE_SWAP`. It uses the exact captured
  `DRAW_INDX`, captured raster/fetch words, captured PS slice, and captured
  index values, with a synthetic VS, constants, and texture payload. This is
  plugin integration evidence, not a live retail frame or parity result. A
  separate synthetic offscreen AutoIndex point-draw smoke passed Vulkan
  validation on Linux and executed on Redmi Note 8 Pro; its vertex shader uses
  `gl_VertexIndex` without a vertex buffer. On
  2026-10-23, Wi-Fi ADB also ran the
  draw-input, guest-ring, shader-translation, and Vulkan 1.1 renderer checks on
  Redmi Note 8 Pro / Android 13 / Mali-G76 MC4. Android validation layers were
  unavailable. A live Linux retail run also loaded the
  emulator-free plugin, initialized the guest ring, and consumed 1,828 PM4
  packets including two swaps. A later live run recorded 100 `DRAW_INDX_2` packets, all AutoIndex (96 point
  draws and four rectangle-list draws). The updated plugin submitted 24 point
  draws and one rectangle draw at each of two 1280x720 guest swaps. It rejected
  the other rectangle variant per swap because captured `mode_control=6` and
  `color_info=0` are outside the decoded raster contract. The live readback
  with the diagnostic magenta fragment override contained 518,400 non-black
  pixels; the [decoded diagnostic image](../evidence/process2_xbox_live_vulkan_magenta_raster_diagnostic_20261023.png)
  shows the captured geometry reaching the Vulkan target. With the captured
  retail pixel shader restored, the readback contained no non-black pixels.
  The game window remained black apart from the cursor, so this confirms live
  Vulkan submission and rasterization only, not visible retail output or scene
  parity. The full evidence and hashes are in
  [`process2_xbox_live_guest_ring_20261023.json`](../evidence/process2_xbox_live_guest_ring_20261023.json).
  No DMA-indexed draw, pointer `IM_LOAD`, or `LOAD_ALU_CONSTANT` was observed.
  The private 19,784-byte capture scans as 247 packets with four bounded
  `DRAW_INDX` packets. The capture decoders reject unsupported forms. The untile
  path rejects other pitches, formats, dimensions, and layouts. Its address
  mapping is cross-checked against the public
  [Xenia `Tiled2D` implementation](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/texture_address.h);
  descriptor enum meanings are cross-checked against the public
  [Xenos register definitions](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/xenos.h).
  These are documentation cross-checks only: this project has no Xenia runtime
  dependency and does not emulate a Xenos GPU;
- the first captured Xbox `DRAW_INDX` (six 16-bit indices, four captured
  `FLOAT3` vertices, the captured 1024x256 texture, constants, and translated
  shaders) has been submitted by `shift_vulkan_bundle_execute` to the
  project-owned Vulkan backend. That path uses Vulkan 1.1, an sRGB color target,
  captured viewport/blend/cull state, and a project-owned Xbox target/gate
  contract. The native run enabled `VK_LAYER_KHRONOS_validation` and reported
  zero validation errors. The output shows the captured SHIFT logo draw; it is
  evidence of one submitted draw, not full-frame retail parity. The source
  capture was obtained with an Xenos diagnostic run, but neither its renderer
  nor its SPIR-V is used by the project-owned Vulkan path. The same offscreen
  bundle also submitted on Android arm64-v8a / Redmi Note 8 Pro (Mali-G76 MC4).
  Android validation layers were unavailable; its output differed from the
  GTX 950 host output by at most 2/255 per RGB channel, so this is a device
  execution check rather than pixel-identical or retail-frame parity;
- Android full-game status: the renderer and ReXGlue Vulkan presenter/surface
  source compile for arm64-v8a with NDK r28.2 / API 33. The complete plugin
  build stops in ReXGlue's POSIX fiber backend because Bionic lacks
  `getcontext`, `makecontext`, and `swapcontext`; that scheduler code belongs
  to Process 1. The repository has a minimal NativeActivity surface-probe
  library, but it does not integrate the game or ReXGlue runtime and there is
  no game manifest/APK target. No full game build has been installed or tested
  on the phone;
- limitations: the standalone capture bundle starts from black because prior
  EDRAM contents were not captured; the black texture-border alpha remains
  unresolved, and the live frontend currently selects transparent-black
  provisionally. The plugin has no dependency on the runtime-loaded
  `rexgpu-xenos` renderer; ReXGlue's common runtime still includes generic
  Xenos format utilities. The Android verification exercises the platform
  independent renderer only, not ReXGlue window presentation. Live retail
  submission is confirmed, but the captured host window remained black apart
  from the cursor, so visible output is not working yet. Full-scene parity is
  not claimed. The product path must not load
  `rexgpu-xenos` or another GPU renderer emulator;
- Linux CI coverage for native smoke paths.

## Rules

1. RenderCommand/1 is the source contract.
2. Native execution targets SPIR-V; GLSL is validation/debug representation.
3. MEB repack decisions stay upstream.
4. Buffers/images/descriptors use explicit contracts.
5. The backend does not infer undocumented game semantics.

## Current limitation

The backend is not yet a complete production renderer. Full BMW
shader/material execution and full RenderCommand submission remain bounded by
shader/reference coverage and runtime evidence. The Xbox work currently covers
one standalone captured draw, live AutoIndex point and rectangle-list draws,
and a small, fail-closed microcode subset. One captured rectangle target state
remains unsupported, and Xenos EDRAM accumulation remains unimplemented.

## Commands

```bash
cmake -S native_vulkan -B native_vulkan/build
cmake --build native_vulkan/build --config Release
ctest --test-dir native_vulkan/build --output-on-failure
./native_vulkan/build/shift_vulkan_probe
./native_vulkan/build/shift_vulkan_headless_clear out/shift_vulkan_headless.ppm
```

The headless path has no window-system dependency.


## RenderCommand provenance gate

BMW bundle preparation accepts `SHIFT.RenderCommand/1` but now blocks native
bundle generation unless the selected submesh passes `SHIFT.NativeSubmissionGate/1`.
That gate requires complete FXO payload provenance and
`SHIFT.ShaderPermutationIdentity/1` for the shader pair.

This is a provenance gate, not a claim of runtime shader equivalence.


## Validate native bundle execution

```bash
python3 tools/run_linux_vulkan_smoke.py out/vulkan/bundle --validation
# Or execute an already prepared bundle directly:
native_vulkan/build/shift_vulkan_bundle_execute out/vulkan/bundle/bundle --validation
```

`--validation` explicitly enables `VK_LAYER_KHRONOS_validation` and its debug
messenger. Install `vulkan-validationlayers` on Ubuntu/Debian. If the layer or
extension is missing, startup fails. Any validation error makes native execution
fail even if a PPM was produced; the Python runner propagates that failure.
Successful native JSON includes `validation_enabled` and `validation_errors`.
Warnings go to stderr. CI requires validation for the mixed-resource smoke run.
Depth image views are created with the depth aspect directly.
