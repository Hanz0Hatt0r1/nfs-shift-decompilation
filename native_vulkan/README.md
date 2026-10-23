# Linux Vulkan backend

The native Vulkan backend consumes the neutral render contracts used by the desktop reference path.

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
  descriptor decoder maps the captured channel selectors, signs, X/Y/Z clamp
  modes, border code, filters, and anisotropy to semantic values; they are not
  yet applied to a Vulkan view or sampler. The captured black border code has
  unresolved alpha, so the backend does not guess a Vulkan border color. The
  captured color/depth target, viewport, and screen/window scissor are also
  decoded into a bounded neutral state contract. This does not map Xenos EDRAM
  tiles to Vulkan images or create a pipeline. The constants decoder resolves
  each stage's 256-register float window and the observed PS branch bools,
  including the VS a0-indexed c0-c3 window.
  A bounded decoder parses the captured VS/PS control-flow slots and their
  `vfetch_full` and `tfetch2D` instructions, plus scheduled ALU operands,
  temporary-register addressing flags, scalar source selectors, and
  component-relative swizzles. The project-owned translator now emits Vulkan
  GLSL for the observed VS/PS pair, including its `b128`/`b129` branch path,
  vertex fetch, captured ALU subset, texture fetch/swizzle, and exports. It
  rejects unsupported control flow and operations. The actual captured pair
  compiled to Vulkan 1.1-compatible SPIR-V and passed `spirv-val`.
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
  supported DMA-source `DRAW_INDX` or `DRAW_INDX_2`, it checks the captured
  raster state, shader programs (including bounded inline `IM_LOAD_IMMEDIATE`
  code), constants, and descriptors; translates the bounded shader pair to
  project-owned GLSL; compiles Vulkan 1.1 SPIR-V; and resolves normalized
  index/vertex payloads plus the untiled texture. At `PM4_XE_SWAP`, the plugin
  batches those draws and submits them into the ReXGlue presenter's output
  image through `shift_xbox_live_vulkan_renderer`. That renderer core has no
  XCB/Wayland dependency. The frame currently starts with a black clear and
  does not reconstruct prior Xenos EDRAM or import the guest frontbuffer as a
  completed image. Regressions cover PM4 draw/swap framing, ring wraparound,
  indirect buffers, and the plugin ABI; the plugin ring smoke checks its
  decoded inline-shader and both indexed-draw counters. A separate offscreen
  indexed-draw smoke passed Vulkan validation on Linux and executed on
  Redmi Note 8 Pro;
  those smoke shaders are synthetic. On 2026-10-23, Wi-Fi ADB also ran the
  draw-input, guest-ring, shader-translation, and Vulkan 1.1 renderer checks on
  Redmi Note 8 Pro / Android 13 / Mali-G76 MC4. Android validation layers were
  unavailable. A live Linux retail run also loaded the
  emulator-free plugin, initialized the guest ring, and consumed 1,828 PM4
  packets including two swaps. A later opcode audit counted 100
  `DRAW_INDX_2` and 14 `IM_LOAD_IMMEDIATE` packets, but no `DRAW_INDX`, pointer
  `IM_LOAD`, or `LOAD_ALU_CONSTANT`. It saved opcode counts, not raw packet
  words, so it does not establish whether those `DRAW_INDX_2` packets use DMA
  indices or AutoIndex. No Vulkan frame was submitted in either run, so a first
  retail draw is not yet confirmed. See
  [`process2_xbox_live_guest_ring_20261023.json`](../evidence/process2_xbox_live_guest_ring_20261023.json).
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
  to Process 1. The game project currently has no Android Activity, manifest,
  or APK target, so no full game build has been installed or tested on the
  phone;
- limitations: the standalone capture bundle starts from black because prior
  EDRAM contents were not captured; the black texture-border alpha remains
  unresolved, and the live frontend currently selects transparent-black
  provisionally. The plugin has no dependency on the runtime-loaded
  `rexgpu-xenos` renderer; ReXGlue's common runtime still includes generic
  Xenos format utilities. The Android verification exercises the platform
  independent renderer only, not ReXGlue window presentation. No live retail
  frame or full-scene parity is claimed. The product path must not load
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
one captured draw and a small, fail-closed microcode subset.

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
