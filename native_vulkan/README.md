# Linux Vulkan backend

The native Vulkan backend consumes the neutral render contracts used by the desktop reference path.

Current retail-device output and Android ARM64 build status are tracked in
[`ANDROID_RENDER_STATUS_20261024.md`](ANDROID_RENDER_STATUS_20261024.md).
The Linux retail loading frame after relative constant addressing, Xenos gamma
conversion, and Copy/Convert channel fixes is recorded in
[`process2_linux_retail_loading_frame10_20261024.json`](../evidence/process2_linux_retail_loading_frame10_20261024.json).
That frame is not evidence of a visible menu or race scene. A Vulkan 1.1
4x-to-1x D24S8 `SAMPLE_ZERO` resolve/load path now has host and Redmi Note 8
Pro hardware regression coverage. A separate, still-open
[ReXGlue PR #2](https://github.com/Hanz0Hatt0r1/rexglue-sdk/pull/2) proposes
the optional provider capability:
it uses Vulkan 1.2 core support or atomically requests the Vulkan 1.1 KHR
extension pair, and reports `SAMPLE_ZERO` only when supported for both depth
and stencil. The plugin feature-detects this API and keeps older SDK builds
fail-closed. The SDK used in the latest retail run does not expose it, so the
run still stops at mixed-sample depth/stencil preservation. The current Xbox
draw frontier and exact limits are recorded in
[`PROCESS2_XBOX_DRAW27_STATUS_20261025.md`](PROCESS2_XBOX_DRAW27_STATUS_20261025.md).
The resolve mode still needs comparison against a subsequent retail frame.
The latest full Android activity exits before producing that frame.

Retail draws #32 and #45 supplied tiled Xenos format-20 DXT4/5 textures, and
draw #44 supplied format-59 DXT5A. The native input path now untile-decodes
these captured base-level layouts to RGBA8 without requiring a Vulkan
BC-compression feature. Descriptor-shaped regressions passed on Linux and
Redmi Note 8 Pro. Retail draw #28's base and mip descriptors alias the same
guest page; the plugin accepts this captured texture as base-level-only.
Distinct mip pages still require captured mip payloads. The latest live draw
and frame-refresh blockers are tracked in
[`PROCESS2_XBOX_DRAW27_STATUS_20261025.md`](PROCESS2_XBOX_DRAW27_STATUS_20261025.md).
See [`process2_retail_dxt4_5_texture_decode_20261024.json`](../evidence/process2_retail_dxt4_5_texture_decode_20261024.json).

## Captured multi-sampler support (2026-10-24)

A live Linux retail capture previously rejected draw #27 because its pixel
shader used multiple samplers. The translator now emits a Vulkan descriptor
binding for each active texture fetch constant, the plugin snapshots each
referenced descriptor and texture independently, and the renderer uploads and
binds each image/sampler pair at that original binding. A synthetic translator
regression and an offscreen draw with distinct textures at bindings 0 and 1
pass. Linux native and plugin CTest suites pass 4/4 each; the renderer test
reports zero Vulkan validation errors on a GTX 950. The Android ARM64 native
build passes, and both the renderer regression and shader translation test
pass on a Redmi Note 8 Pro / Mali-G76 MC4. This is implementation and device
coverage, not proof that retail draw #27 now renders or that the frame matches
the original. The complete ReXGlue Android plugin build remains blocked in its
existing Bionic-incompatible POSIX fiber source. Details and limitations are
recorded in
[`process2_retail_multi_sampler_vulkan_20261024.json`](../evidence/process2_retail_multi_sampler_vulkan_20261024.json).

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
  decoded into a bounded neutral state contract. A CPU-side address helper now
  maps 32bpp 1x/2x/4x samples to the 10 MiB Xenos EDRAM tile address space,
  including the depth half-tile swap. It does not back Vulkan attachments,
  preserve raster writes between target changes, or support paired-tile 64bpp
  color. A separate strict decoder now
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
- Android full-game status: the project-owned ARM64 renderer plugin has been
  built against the unchanged runtime DSO from the already-built game APK and
  installed on the Redmi Note 8 Pro. The latest candidate displays the retail
  Loading screen, all six language-selector labels, the title sequence, and
  the safety disclaimer. This is a plugin replacement in an existing APK, not
  a complete Android runtime rebuild: the SDK's POSIX fiber source still uses
  `getcontext`, `makecontext`, and `swapcontext`, which Bionic does not expose.
  That scheduler implementation belongs to Process 1. Current hashes and
  screenshots are in
  [`process2_android_descriptor_layout_live_candidate_20261026.json`](../evidence/process2_android_descriptor_layout_live_candidate_20261026.json);
- limitations: the standalone capture bundle starts from black because prior
  EDRAM contents were not captured; the black texture-border alpha remains
  unresolved, and the live frontend currently selects transparent-black
  provisionally. The plugin has no dependency on the runtime-loaded
  `rexgpu-xenos` renderer; ReXGlue's common runtime still includes generic
  Xenos format utilities. The early standalone capture-bundle smoke was not
  visible in its host window, but later exact-XEX runs and the current Redmi
  candidate do show original retail output. Menu-after-disclaimer, race
  scenes, sustained live Bink playback, and full-scene parity are not
  established. Android validation-layer coverage is unavailable. The product
  path must not load
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
and a small, fail-closed microcode subset. The observed 1280x720 source-0/sample-0
color Copy/Convert form is decoded and submitted through a Vulkan resolve pass;
other Xenos EDRAM copy/resolve forms and EDRAM accumulation remain unsupported.
The current Redmi evidence records 1,090 accepted Copy/Convert operations paired
with 1,090 presenter submissions, but does not establish post-disclaimer menu,
race rendering, or full retail parity.

## Latest Redmi renderer candidate and retail boundary (2026-10-26)

The latest Android package was rebuilt with the P2 renderer source through
`345fc2ef69f485ab3f2f15effbb4d837be96c51` and installed incrementally on the
Redmi Note 8 Pro. Its APK SHA-256 is
`35383e756421c4d92264e02f3e9da3eafc52db22febe6c316d15007c0076cd3b`; the
ARM64 renderer DSO SHA-256 is
`9d7ee9ee95b38497ed37f7cf72365a1bcb250560c4d387ab635272de9bd90a0d`. Only
the two GPU-plugin APK payload entries changed; the existing runtime DSO was
kept byte-identical. The package signature and 16-KiB alignment checks passed.
The recorded screenshots show the original loading screen, all six language
labels, and readable safety text. See the
[`candidate record`](../evidence/process2_android_descriptor_layout_live_candidate_20261026.json).

The corresponding Linux renderer source was handed to Process 1 and loaded
with its matching runtime. The available P2 retail log shows startup draw #0
arriving before a complete raster-register state (`valid_mask=0x17038`) and
being rejected fail-closed; subsequent observed batches were submitted. The
initial Android install capture had no per-frame plugin log; a later
read-only check found its process absent, with unknown cause. A fresh relaunch
of the same installed APK is recorded below. No post-disclaimer menu, new Bink
frame from the current Android candidate, or race-scene draw has been
captured. The nearby `menu_background.xml` open failures are a Process 1
runtime/content observation and do not establish the cause of the stalled
screen.

## Fresh Redmi relaunch (2026-10-26)

The APK installed on the Redmi was re-hashed on device and matches the
candidate exactly (`35383e75…0076cd3b`). I launched it from the Android
launcher without reinstalling or clearing data. The app displayed the original
legal disclaimer; two screenshots 28 seconds apart are byte-identical. Its
`shift-native` log records 495 live draw submissions and 495 accepted
source-0/sample-0 Copy/Convert operations, zero Vulkan refresh failures, and
zero rejected PM4 draw packets. The only unresolved draw is the early draw #0
with incomplete raster state (`valid_mask=0x17038`), still fail-closed.

Four failed `menu_background.xml` opens follow the last 14-draw renderer batch;
the run does not establish causality. The app was left foregrounded. See the
[`Redmi relaunch evidence`](../evidence/process2_redmi_latest_candidate_live_disclaimer_20261026.json),
[device screenshot](../evidence/process2_redmi_latest_candidate_live_disclaimer_20261026.png),
and [captured runtime log](../evidence/process2_redmi_latest_candidate_live_disclaimer_20261026.log.gz).
This confirms a stable disclaimer frame on Mali-G76 MC4; it does not verify
the menu, race, or full-scene parity. Android validation-layer coverage is
unavailable.

## Fresh exact-XEX retail check (2026-10-26)

I launched the exact retail XEX with the latest Process 2 Linux plugin and its
matching runtime. The loaded plugin hash is `78d02ba8…c08fc61d6`; the process
map contains no `rexgpu-xenos`. The Vulkan window shows the original safety
disclaimer and its thin purple strips. Across this log snapshot, 1,139 live
draw batches were submitted with 1,139 accepted source-0/sample-0
Copy/Convert operations, no PM4 draw rejections, and no Vulkan refresh
failures. The sole unresolved draw remains the early draw #0 with incomplete
raster state (`valid_mask=0x17038`), which stays fail-closed.

The last captured 14-draw batch is followed by failed opens of
`menu_background.xml`; the run records no later menu or race draws. This
timing does not establish causality or a renderer defect. The exact build,
log snapshot, screenshot, and limitations are recorded in the
[`Linux retail evidence`](../evidence/process2_linux_current_renderer_disclaimer_20261026.json).
The live retail process did not enable the Vulkan validation layer; renderer
validation coverage remains from the separate host regression runs.

A single `KEYCODE_BUTTON_A` was then injected into the active Redmi app while
it showed the disclaimer. Ten seconds later, the screenshot hash was unchanged,
the same app process remained top-resumed, and the guest log matched the earlier
snapshot byte-for-byte. The event's delivery to the guest is unconfirmed; no new
draw contract was captured. See the
[`post-disclaimer input probe`](../evidence/process2_redmi_disclaimer_after_a_20261026.json)
and [captured frame](../evidence/process2_redmi_disclaimer_after_a_20261026.png).

## Fresh Redmi disclaimer-border check (2026-10-26)

The installed provider-resolve APK was still running on the Redmi Note 8 Pro.
Its live plugin mapping hashes to the same DSO as the packaged Process 2 Vulkan
plugin. The current phone screenshot shows the original legal text and two
continuous, neutral-gray horizontal rules. Compared with the earlier Redmi
screenshot containing purple dotted strips, the text body differs by at most
two intensity levels while the large changes are confined to the rule bands.
The core line rows are 281–282 and 812–813 in the 2340×1080 phone screenshot;
their mean RGB is (145.8, 145.8, 145.8). This verifies the disclaimer border
path on the live device, without claiming a console-reference color comparison.

The captured log records 1,587 Vulkan draw submissions and 1,589 accepted
source-0/sample-0 Copy/Convert operations. One 14-draw transition frame at
22:42:34 MSK was rejected for unsupported target/Copy extent; later 13-draw
disclaimer submissions continued. Draws #0–13 on that transition remained
fail-closed. Four failed opens of `menu_background.xml` immediately before it
do not establish the cause of the absent menu. The app remains on the
disclaimer; a center tap and Enter left its screenshot byte-identical, and
delivery of those inputs to the guest is unconfirmed.

See the [live evidence record](../evidence/process2_redmi_provider_resolve_disclaimer_live_20261026.json),
[phone screenshot](../evidence/process2_redmi_provider_resolve_disclaimer_live_20261026.png),
and [compressed guest log](../evidence/process2_redmi_provider_resolve_disclaimer_live_20261026.log.gz).
The native Vulkan build and four host CTest checks passed. The resolve-capable
plugin also built with Clang and all seven plugin CTest checks passed with
`VK_LAYER_KHRONOS_validation` forced through the loader. The phone run did not
enable Vulkan validation layers; language-menu continuity, cutscenes, race
graphics, and full retail parity remain unverified.

## Exact disclaimer-strip replay on Mali (2026-10-27)

The Android ARM64 `xbox_live_vulkan_renderer_check` now links the captured
draw-input decoder required by its retail texture fixture. The checker was
built with NDK r28c and run offscreen on the Redmi Note 8 Pro (Android 13,
Mali-G76 MC4) using the captured 512x8 DXT4/5 texture, decoded RGBA8 pixels,
four retail vertex payloads, and translated Vulkan 1.1 shaders. The four
captured draws passed; the output contains two continuous horizontal rules
without gaps. The game activity remained resumed.

The [Mali replay record](../evidence/process2_mali_disclaimer_exact_replay_20261027.json)
and [decoded output](../evidence/process2_mali_disclaimer_exact_replay_20261027.png)
preserve the hashes. Android validation layers were not enabled for this
shell run; the corresponding host replay passed with
`VK_LAYER_KHRONOS_validation`. This replay covers the four rule draws only.
It does not establish an independent retail reference for their color,
thickness, position, or whether vertical sides should exist. The currently
installed APK still contains an older renderer DSO, so this is not a fresh
full-app capture.

### Captured transition Copy/Convert sequence

The same phone log records a sequence of internal mode-6 copies before the
presenter copy. One selects all four source samples, clears color and depth,
and converts to a 1280x720 format-26 destination with unsigned number format
and exponent bias 11. Seven following copies target distinct addresses and
extents in format 31 (`16_16_FLOAT`), selecting sample 0 and clearing color.
The final accepted copy to `0x0975E000` is a separate 1280x720 sample-0
frontbuffer operation.

The 14-draw refresh error does not identify whether target format or source
extent rejected the batch. The P2 submit model retains one draw vector and one
Copy/Convert operation per swap; it does not write intermediate copy results
back to guest memory. Rendering this capture therefore needs ordered
intermediate target/copy execution before the final frontbuffer pass. The
different intermediate sizes resemble a downsample chain, but that purpose is
not proven by this capture. Exact register values, field decoding, log hashes,
and limitations are in
[`process2_redmi_transition_copy_chain_20261026.json`](../evidence/process2_redmi_transition_copy_chain_20261026.json).
Field meanings use the Xenos register layout in
[`registers.h`](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/registers.h).

## Single-target submission guard (2026-10-27)

The renderer now rejects a draw batch if captured color or depth base tiles
change within that submission. The existing submit path creates one Vulkan
attachment and cannot model Xenos EDRAM target switching; silently merging
different bases could produce a plausible but incorrect image. A regression
uses equal-sized draws with different color bases and confirms the batch fails
before submission. The error includes the first draw index and both before/after
base values. Host renderer CTest passed 4/4 with
`VK_LAYER_KHRONOS_validation`, plugin CTest passed 6/6 with the same layer,
and the ARM64 renderer-check passed offscreen on the Redmi Note 8 Pro / Mali-G76
MC4. The running app stayed foregrounded and its screenshot hash did not
change. This is a fail-closed boundary, not implementation of the captured
intermediate target/copy chain. The Android ARM64 plugin now builds when linked
against the exact runtime DSO already packaged in the installed APK; rebuilding
that runtime from the external SDK still hits its Android POSIX fiber/memory
errors. The new plugin was not installed. Details and build identifiers are in
[`process2_multitarget_guard_20261027.json`](../evidence/process2_multitarget_guard_20261027.json).

## Xenos EDRAM sample addressing (2026-10-27)

`captured_xenos_edram_sample_address` maps captured 32bpp target pixels and
their 1x/2x/4x samples into the 10 MiB, 80x16-sample, 2048-tile EDRAM address
space. The 4x target uses 2x2 sample expansion; depth addresses apply the
40-sample half-tile swap. These layout constants and sample dimensions are
documented in the [Xenos register definitions](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/xenos.h); the project only uses that file as a read-only hardware-layout reference.

This helper returns an address only. It does not allocate or populate Vulkan
EDRAM storage, execute the mode-6 intermediate copies, or restore aliased
samples when the retail batch changes target layouts. The regression pins the
14-draw layout sequence from the Redmi capture and confirms it still fails
closed at draw 1. Host CTest passed 4/4 with Vulkan validation; the ARM64 input
check and a synthetic Vulkan 1.1 offscreen smoke passed on Mali-G76 MC4. The
phone remained on the legal disclaimer, so this change establishes no video
or retail-frame parity. Full capture and test details are in
[`process2_xenos_edram_sample_mapping_20261027.json`](../evidence/process2_xenos_edram_sample_mapping_20261027.json).

## Intermediate Copy/Convert output primitives (2026-10-27)

The renderer now has narrowly gated Vulkan fragment paths for the captured
format-26 all-four-sample conversion to `R16G16B16A16_UINT` and format-31
sample-zero copy to `R16G16_SFLOAT`. Format 31 is exercised with both 1x and
4x source images. The Vulkan smoke supplies a full-screen synthetic source and
checks exact destination texel values; it does not use this result as retail
parity evidence. The new shaders compile for `vulkan1.1` and pass
`spirv-val --target-env vulkan1.1`. Host renderer CTest passed 4/4 with
`VK_LAYER_KHRONOS_validation` on NVIDIA GeForce GTX 950.

These paths render to a caller-owned Vulkan image. They do not apply guest
destination endianness as bytes in guest memory, perform the Copy/Convert
color/depth-clear side effects, cache the result by guest GPU address/layout,
or preserve aliased EDRAM across target changes. The plugin still does not
execute the captured 14-draw operation stream. PM4 capture now retains each
Copy/Convert packet's own compiled shaders and raw source registers, and the
renderer rejects a copy packet without a prepared payload. This prepares the
operation boundary but does not submit its intermediate image. See
[`process2_copy_convert_primitives_20261027.json`](../evidence/process2_copy_convert_primitives_20261027.json)
for the exact tested tuple and limits.

## Captured Copy/Convert EDRAM clear side effects (2026-10-28)

The ordered Vulkan submit path now applies the captured post-Copy/Convert clear
to its source EDRAM attachment using the Copy packet's captured rectangle
geometry. The verified subset is deliberately narrow: both raw color clear
registers must be zero, and an enabled D24S8 depth clear must be exactly
`0xFFFFFF00` (depth 1.0, stencil 0). The renderer rejects missing clear
registers, unsupported values, missing captured geometry, and depth clears on
non-D24S8 sources before submission. Clear draws preserve the source attachment
outside the captured rectangle and keep color/depth images in Vulkan 1.1
layouts with explicit barriers.

Regressions run the format-26 four-sample path with color and depth clear
enabled, the format-31 color-only path, and an ordered format-31 cached-source
clear followed by a presenter Copy/Convert. The latter reads back zero from the
persisted target after the clear. Host CTest passed 4/4; the renderer test also
passed with `VK_LAYER_KHRONOS_validation`; Linux ReXGlue plugin CTest passed
6/6. The clear shader passes `spirv-val --target-env vulkan1.1`. These are
synthetic renderer checks; depth/stencil clear values have not yet been
independently read back and compared, and this does not execute the complete
retail 14-draw transition. See
[`process2_ordered_edram_copy_clear_20261028.json`](../evidence/process2_ordered_edram_copy_clear_20261028.json)
for build details and limits.

The Android ARM64 renderer/check targets compile with NDK r28c. The current
device has no ADB connection, so this revision has not been run on the phone.
Shared physical EDRAM storage across overlapping target aliases, sample/format
reinterpretation, complete Copy/Convert source association, and full
depth/stencil preservation across the captured target switches remain open.

### Captured alias-tile mapping (2026-10-28)

The address layer now enumerates physical EDRAM tiles shared by two captured
layouts and reports each tile's source and destination coordinates. It rejects
layouts whose full extent wraps a physical tile more than once, because mapping
those Vulkan pixels back to one EDRAM tile requires captured draw coverage and
ordering. A regression based on the transition's 4x/pitch-640 and
1x/pitch-1280 views maps all 720 common tiles and checks every one of the 1,280
sample slots in a tile for both color and depth. Each source and destination
sample resolves to the same physical EDRAM byte address; this is address
mapping evidence, not a resolve or a rendered frame.

The earlier 2560x1440 4x layout spans 2,880 virtual tiles under the current
32bpp address model, so the new unique-tile mapper rejects it. The metadata
alone does not show which tiles its captured draws touch; the model does not
use per-draw scissor/geometry coverage. Physical Vulkan backing and data
transfer across aliases are still unimplemented. Native CTest passed 4/4 and
Linux plugin CTest passed 6/6 under `VK_LAYER_KHRONOS_validation`; Android
ARM64 renderer and checker targets compiled, but no device was connected. See
[`process2_edram_alias_tile_map_20261028.json`](../evidence/process2_edram_alias_tile_map_20261028.json).
`captured_xenos_edram_raster_tiles` now enumerates wrapped virtual raster tiles
without discarding repeated physical EDRAM indices. The captured draw-0 layout
enumerates 2,880 raster tiles and aliases 832 physical tiles twice in both
color (base 0) and depth (base 1024). The renderer still rejects transfer
from that layout because it has no captured draw-coverage/order mapping to
decide which Vulkan pixels represent each physical tile.
When an ordered stream hits an alias, its rejection now reports source and
destination raster-to-physical tile counts plus a repeated-tile coordinate
example. The retail draw-0/draw-1 regression checks the exact color and depth
wrap diagnostics during preflight, before any draw reaches Vulkan.

## Conservative EDRAM layout switching (2026-10-27)

The ordered-stream preflight now computes color and depth tile footprints for
each captured layout, including 1x/2x/4x addressing and the 2048-tile
wraparound. It permits a later draw stage to use a separate cached Vulkan image
only when its whole-tile footprint is disjoint from every layout already seen.
An exact previously seen layout can reuse its image. A copy-only packet still
requires an initialized exact-layout source; when the Copy/Convert source
registers decode, a copy after draws rejects a different captured source
layout. This keeps cached images from silently standing in for shared physical
EDRAM.

Regressions cover identical layouts, disjoint color/depth ranges, address wrap,
color-to-depth aliasing, ordered Draw/Copy/Draw/Copy on disjoint layouts, and
rejection of an aliased layout. Host CTest passed 4/4 with
`VK_LAYER_KHRONOS_validation`. The Linux ReXGlue DSO was rebuilt with SDK
revision `b3648b013b02770fa5ca8d4618235b2326c911ca`; its six plugin CTests also
passed with validation enabled. The ARM64 plugin linked against the exact
`librexruntime.so` extracted read-only from the installed APK; that DSO was not
installed and the game stayed open. The device went offline before the new
ARM64 input regression could be executed there. These are synthetic layout and
Vulkan checks, not retail rendering evidence. The exact 1280x720 packet-27
color alias is handled by the narrow path below. Larger wrapped layouts and
other transitions in the captured 14-draw sequence remain unsupported;
general shared EDRAM storage, partial-copy clear effects, depth/stencil
persistence, and full resolve behavior remain open. Build hashes and limits are in
[`process2_ordered_edram_tile_disjoint_20261027.json`](../evidence/process2_ordered_edram_tile_disjoint_20261027.json).

### Reverse EDRAM sample coordinates (2026-10-27)

The address layer now reverses an unwrapped EDRAM tile coordinate and
tile-local sample slot to the logical pixel and MSAA lane for a captured
layout. It inverts the depth half-tile swap and rejects padding samples in a
partial edge tile. The regression includes the retail draw-0/draw-1 layouts:
physical color tile 16, sample slot 0 maps to pixel `(640, 0)` in draw 0 and
`(0, 8)` in draw 1. This makes the aliased coordinate relationship explicit
for a future shared EDRAM transfer path.

This address work now feeds one captured color transfer path described below.
It still does not create a general physical EDRAM backing store or preserve
depth/stencil across the full retail sequence. The captured transition is not
rendered end to end. Details and CPU regression scope are in
[`process2_edram_reverse_sample_mapping_20261027.json`](../evidence/process2_edram_reverse_sample_mapping_20261027.json).

### Captured packet 27 EDRAM color alias transfer (2026-10-28)

The ordered path handles one exact capture transition: a 1280x720 4x
`RGBA8_GAMMA`, pitch-640 target changes to a 1x `RGBA8_LINEAR`, pitch-1280
view over the same color/depth bases, then immediately executes a sample-zero
format-6 Copy/Convert to `0x0975E000`. The tile map for this pair is identity
across 720 shared color and depth tiles. The renderer now submits the prior
draw stage, keeps its 4x image in the EDRAM cache, and transfers each tile-local
sample into the matching pixel of a persistent 1x color target before packet
27. The transfer is enabled only when packet 27 has depth/stencil disabled,
the following copy reads the exact 1x layout, and its destination tuple
matches the capture. Other transitions remain rejected. The prior 4x depth
image remains intact; this path does not convert depth or stencil.

The Vulkan smoke regression compares the ordered 4x-to-1x transfer with an
equivalent 1x renderer stream and requires identical output readback. It also
checks that a changed pitch is rejected. Native Vulkan CTest passed 4/4 with
`VK_LAYER_KHRONOS_validation`; the Linux ReXGlue plugin suite passed 7/7.
Both transfer shaders pass `spirv-val --target-env vulkan1.1`. The Android
ARM64 renderer and check targets compile. ADB reports no attached device, so
there was no phone run. This is executor evidence with synthetic test shaders,
not retail pixel parity. A later bounded retail replay did submit a matching
14-draw/Copy38 operation stream, but without image readback; intermediate
pixel correctness, other transition batches, and a full game frame remain
unverified. The capture and interrupt audit are recorded in
[`process2_ordered_edram_packet27_alias_transfer_20261028.json`](../evidence/process2_ordered_edram_packet27_alias_transfer_20261028.json)
and
[`process2_gpu_backend_resolvepr2_source1_interrupt_join_20261028.json`](../evidence/process2_gpu_backend_resolvepr2_source1_interrupt_join_20261028.json).

### Captured 14-draw sequence with Copy/Convert packet 38 submitted (2026-10-28)

A bounded Linux Native replay loaded the retail XEX and the resolve-capable P2
`shift-native` plugin with GPU emulation disabled. Its ordered-operation log
contains the same signature as P1's paired capture: Draw packets 0 through 13,
then Copy/Convert packet 38 to frontbuffer `0x0975E000`. The P2 presenter log
then reports 14 indexed draws submitted. Draw ordinal 2 was selected from
presenter frame 622; its original VS/PS hashes match the tracked retail shader
fixtures and pass the existing translation and Vulkan 1.1 SPIR-V checks.

The P1 and P2 operation signatures and capture identities match, but P1 did not
record a selected shader frame/ordinal for that exact occurrence. The shader
bytes are therefore mapped to the P2 replay's ordinal 2, not asserted as a
byte-for-byte join to the P1 instance. This P2 run did not request a readback,
so it proves ordered operation submission only, not intermediate pixel
correctness or retail visual parity. The bounded GDB run also ended with
partial event-log recovery and exit code 1 after an empty-command error at
trace script line 1167. No Android device was attached. Exact hashes, packet
order, submit evidence, and limits are in
[`process2_ordered_14draw_copy38_replay_20261028.json`](../evidence/process2_ordered_14draw_copy38_replay_20261028.json).

### Frame 622 readback of the 14-draw Copy38 stream (2026-10-28)

A separate bounded Linux Native capture selected presenter frame 622 while
the renderer held the same 14 Draw packets 0..13 followed by Copy/Convert
packet 38. The original retail disclaimer text and horizontal borders appear
in the Vulkan readback:
[`decoded frame 622`](../evidence/process2_ordered_14draw_copy38_frame622_20261028.png).
The complete packed presenter image and its pre-Copy source are available as
compressed raw captures:
[`A2B10G10R10 output`](../evidence/process2_ordered_14draw_copy38_frame622_presenter_a2b10g10r10.bin.gz),
[`RGBA16 pre-Copy source`](../evidence/process2_ordered_14draw_copy38_frame622_precopy_rgba16_unorm.bin.gz).

The renderer snapshot records target layouts for packets 0–13: 4x color at
pitch 640, a 4x depth-only view, 1x color at pitch 1280 for packets 2–10, a
second 4x depth-only view, and 1x color for packets 12–13. All views use
color base 0 and depth base `0x2d0`; Copy38 follows. The readback confirms that
this captured sequence reached the presenter. It does not prove independent
Xenos depth/stencil contents or general EDRAM alias behavior.

The 1280x720 pre-Copy source is single-sample `R16G16B16A16_UNORM`; the
presenter image is `A2B10G10R10_UNORM_PACK32`. After the Copy's 16-bit to
8-bit to 10-bit UNORM quantization, 920,250 of 921,600 pixels match exactly
and every other pixel differs by at most one 10-bit code value. This checks
the captured Copy output against the renderer's own source image for this
retail frame. It does not compare the pre-Copy EDRAM contents with Xenos output
or establish general EDRAM/depth preservation; the grayscale frame also cannot
test the captured red/blue swap. The bounded GDB trace again ended with partial
event recovery and exit code 1. Full hashes and limits are recorded in
[`the readback evidence`](../evidence/process2_ordered_14draw_copy38_frame622_readback_20261028.json).

The same run's recovered source-1 PM4 interrupt records are archived as
[`JSONL.gz`](../evidence/process2_ordered_14draw_copy38_frame622_source1_interrupts.jsonl.gz).
The archive contains 1,428 sequential interrupt ordinals on ring
`0x09752580`, generation 1. Each record reports CPU mask `0x04` and one
invoked CPU 2 dispatch to `0x823B37B8` with data `0xB7365F00`; read/write
pointers are dword offsets in an 8,192-dword ring and each wraps once. The
partial GDB event recovery retained 737 nested source-1 guest callback entries
(303 at `0x823A4758`, 434 at `0x823B8C60`), preserved verbatim in a separate
[`callback JSONL.gz`](../evidence/process2_ordered_14draw_copy38_frame622_source1_guest_callbacks.jsonl.gz).
Those callback entries are recorded separately: this capture does not establish
a one-to-one join with the outer PM4 interrupt records. A separate
[`timestamp-nearest candidate map`](../evidence/process2_ordered_14draw_copy38_frame622_source1_callback_nearest_pm4_candidates.jsonl.gz)
retains the nearest packet ordinal and ring pointers for each callback: 735 of
737 candidates are within 50 ms, and the candidate ordinals are nondecreasing.
The heuristic maps to 603 distinct interrupts (134 candidates share an
interrupt; 133 interrupts in the candidate span have none). It is useful for
triage, but is not proof of callback semantics or dispatch identity. The trace,
candidate map and limits are checked by the ordered replay regression.

### Captured format-26 Copy/Convert texture fetch (2026-10-28)

Draw #10's captured texture descriptor decodes to guest address `0x0BE19000`,
format 26, endian mode 1, integer format, tiled 1280x720 storage with pitch
1280, and a `0x730000` byte tiled footprint. The preceding captured operation
chain writes that address with 1280x720 format-26 Copy/Convert operations
using sample-select 6 (all source samples), color and depth clear enabled,
and the captured destination format/number/endian/exp-bias tuple. The descriptor
and Copy/Convert register values are taken from the Redmi capture, not inferred
from a rendered image.

The plugin now treats this descriptor as a Copy/Convert texture only when the
same ordered operation batch contains a preceding copy with the exact captured
destination, extent, format 26, unsigned number format 2, endian 1, exp-bias
11, sample-select 6, both clear flags, and the remaining captured control
fields. The Vulkan render destination remains
`VK_FORMAT_R16G16B16A16_UINT`; a compatible UNORM view supplies the sampled
image, and translated integer-format fetches scale normalized components by
65535. Unmatched format-26 descriptors fail closed rather than uploading raw
64bpp guest memory.

The regressions check the captured descriptor decode, reject a descriptor with
the integer-format bit cleared, and run an ordered synthetic draw/copy/draw/copy
stream whose format-26 cached sample changes readback relative to a zero-filled
baseline. Linux Vulkan validation and the Android ARM64 renderer/checker builds
pass. The capture itself predates this change and was collected with an older
plugin; no run has yet shown the new plugin processing the retail descriptor.
This is synthetic executor evidence, not retail pixel parity. The transition's
other draws, format-31 intermediate copies, shader control flow, and final game
frame remain unresolved. Build identity and scope are in
[`process2_ordered_edram_format26_texture_fetch_20261028.json`](../evidence/process2_ordered_edram_format26_texture_fetch_20261028.json).

## Retail conditional-jump rejection detail (2026-10-27)

The Redmi capture also rejects shader translation at draw #14 for a conditional
jump with predication or a non-forward direction bit. The original log did not
say which decoded field triggered the guard, and the retail shader bytes were
not retained. The translator now includes the branch address, bool constant,
condition, unconditional/predicated flags, and direction bit in the rejection.
The guard still rejects the shader; this change does not guess its execution
semantics. A synthetic regression verifies those fields, and the updated
ARM64 translator check passed on the Redmi while the game remained running.
The plugin was built but not installed. See
[`process2_retail_cjmp_diagnostic_20261027.json`](../evidence/process2_retail_cjmp_diagnostic_20261027.json).

## Current Redmi language-selector observation (2026-10-27)

The currently installed older Android build is running on the Redmi Note 8 Pro
at the original language selector. English, French, Italian, German, Spanish,
and Dutch labels are readable. No input was sent; the app was left open. The
installed APK/plugin/runtime hashes and screenshot are recorded in
[`process2_redmi_language_selector_current_installed_20261027.json`](../evidence/process2_redmi_language_selector_current_installed_20261027.json).
This does not verify the current P2 branch or the retail 14-draw transition.

The latest ARM64 draw-input, guest-ring, shader-translation, and offscreen
renderer checks passed on this device. Seventeen generated SPIR-V modules also
passed `spirv-val --target-env vulkan1.1`. These checks use synthetic fixtures;
the Android Vulkan validation layer is unavailable, and the transition is not
yet rendered end to end. Hashes and scope are recorded in
[`process2_android_arm64_renderer_checks_20261027.json`](../evidence/process2_android_arm64_renderer_checks_20261027.json).

## Exact-runtime Process 1 PM4 trace build (2026-10-27)

The Linux plugin now builds against the exact ReXGlue runtime used by the
Process 1 host even though that older SDK shape has no separate
`rexui-vulkan` target. The instrumented plugin records PM4 interrupt packet
identity, ring context, requested/dispatched CPU masks, and per-CPU callback
address/data/status, with the bounded ring trace enabled for this build. Its
SHA-256, build ID, exact host/XEX/runtime identity, and smoke result are in
[`process2_p1_exact_pm4_trace_plugin_20261027.json`](../evidence/process2_p1_exact_pm4_trace_plugin_20261027.json).
Process 1 ran this DSO with the identified host and XEX. Its 2,912 source-1
interrupt rows all reported CPU mask/dispatched mask `0x04` and callback
`0x823B37B8` with data `0xB7365F00`; the bounded guest breakpoint trace recorded
2,810 callback entries through interrupt #2809. The remaining 102 plugin rows
were outside that guest trace's recording window. The `WAIT_REG_MEM` after
interrupt #1094 at physical address `0x1B964004` correctly observed 1 as
unequal to zero, then 0 after 14 ms. This confirms the wait's observed
condition, but does not identify the writer or explain the negative guest
worker counter. The full crosswalk and interpretation limits are in
[`process2_p1_source1_interrupt_crosswalk_20261027.json`](../evidence/process2_p1_source1_interrupt_crosswalk_20261027.json).

## Process 1 source-1 interrupt join, v46 (2026-10-28)

The v46 post-Bink capture recorded 1,925 P2 `PM4_INTERRUPT source=1` rows and
932 nested P1 callback entries. A strict one-to-one timestamp/order audit finds
one continuous P2 ID window, 965..1896, for those P1 callbacks. All matched
rows use generation 1, ring `0x09752580`, CPU/dispatched mask `0x04`, and the
same outer callback wrapper/data. Absolute timestamp deltas range from 0 to
156 ms (median 20 ms). The 993 P2 rows outside that window fall outside P1's
registered-callback observation interval and are not failures.

This confirms ordered callback correspondence, not that callback payloads are
equivalent or that each interrupt is a fresh GPU completion. Reused command
buffer locations and repeated queue tokens remain visible; the guest worker
counter underflows to -187 in this capture, but its meaning remains unresolved.
The capture used plugin `fff4c40c…`, before the later accepted-draw raster
formatter, and did not establish a retail Vulkan frame. The full per-event
join and capture hashes are in
[`process2_v46_source1_interrupt_join_20261028.json`](../evidence/process2_v46_source1_interrupt_join_20261028.json).

## Process 1 source-1 interrupt join, resolve PR #2 (2026-10-28)

The resolve-provider replay used P2 DSO `07a953e6…b304ca9e` from source
`f6f0472…3846f01`. Its paired P1 Native run spans 2026-10-28
01:15:34.928–01:17:52.902 UTC; callback rows in the audit span
01:16:10.567–01:17:50.056 UTC. This is a different P2 build from the later
draw-10 shader replay (`d01405cc…d6d90`); those callback counts are not a
row-for-row comparison.

The resolve-provider replay recorded 1,803 P2 `PM4_INTERRUPT source=1` rows,
with no malformed ring records. A unique one-to-one timestamp/order audit
matches 1,063 P1 callback entries to contiguous P2 interrupt IDs 709..1771.
Every joined row has generation 1, ring `0x09752580`, packet ordinal and ring
read/write pointers, CPU/dispatched mask `0x04`, dispatch CPU 2, and an invoked
outer wrapper `0x823B37B8`. Absolute timestamp deltas range from 0 to 93 ms.
P1 observed registered callback targets `0x823A4758` (375 entries) and
`0x823B8C60` (688 entries); P2 logs the enclosing wrapper dispatch.

`python3 -m unittest native_vulkan.tests.test_audit_pm4_interrupt_join -v`
checks the checked-in per-event join for contiguous IDs, masks, dispatch
status, ring bounds, and timestamp limits. This proves a consistent ordered
correspondence in the capture, not callback payload equivalence or guest
semantic equivalence. The full trace, hashes, and limits are in
[`process2_gpu_backend_resolvepr2_source1_interrupt_join_20261028.json`](../evidence/process2_gpu_backend_resolvepr2_source1_interrupt_join_20261028.json).

## P1 Native queue-wait run: same-run source-1 interrupt join (2026-10-28)

Process 1 supplied its completed Native queue-wait capture, which used P2
plugin `d01405cc…d6d90` and recorded both renderer PM4 ring interrupts and
guest callback entries in one run. The exact normalized inputs are archived in
[`the join input trace`](../evidence/process2_p1_native_queuewait_r2_source1_join_inputs_20261028.jsonl.gz).
A unique strict timestamp/order join matches all 853 guest callback entries to
continuous renderer interrupt IDs 699–1551. The absolute time delta is 0–79 ms
(median 21 ms); all rows report source 1, ring `0x09752580`, generation 1,
CPU/dispatched mask `0x04`, and an invoked CPU 2 dispatch through
`0x823B37B8`/`0xB7365F00`.

This is a same-run ordered correspondence, not proof that callback payloads are
equivalent or that the guest queue head/tail advanced. The full 1,574-row ring
trace has unique contiguous interrupt IDs, while 131 source-IB locations and
many ring pointer values repeat; this does not distinguish intentional command
reissue from duplicate processing. Process 1's capture shows
`sub_823B34A0` still polling its software queue predicate at the bounded stop;
the renderer trace does not establish the cause. The per-row audit and run
identities are in
[`the join record`](../evidence/process2_p1_native_queuewait_r2_source1_interrupt_join_20261028.json),
and the regression replays the join from its archived inputs.

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

## PM4 interrupt order Android smoke (2026-10-26)

A new ARM64 Vulkan plugin was linked against the unchanged runtime extracted
from the installed Redmi APK. The package keeps both legacy GPU plugin aliases
pointing to the same Vulkan DSO; all other APK payloads were hash-compared
unchanged. Incremental install preserved app data. The retail loading frame
appeared at 15 seconds and the safety disclaimer at 40 seconds. The selector
was skipped because English was already saved; the preceding same-device live
capture shows all six labels readable. At the 40-second capture NFS was
top-resumed. A later read-only check found PID 21346 alive and the NFS screen
black after a brief focus change to `vegros101.greatexpanse`; no app stop was
issued. An A event sent after a screenshot showed that other package in the
foreground is not considered an NFS test, and its effect is unknown.

The x86_64 and ARM64 plugin artifacts, APK hashes, screenshots, checks, and
limits are in the [`PM4 Android smoke record`](../evidence/process2_pm4_interrupt_order_android_smoke_20261026.json).
This verifies startup output for the packaged renderer, not retail gameplay or
full visual parity. The existing purple strips remain on the disclaimer
capture; the later black screen and brief focus change do not establish
causality. Android
validation-layer coverage was unavailable.

The latest Linux AMD64 handoff DSO was built from renderer commit
`0f5e9f11b16764b1e62f251aaa17f8e4769da8a6` and passed all six plugin CTest
checks with `VK_LAYER_KHRONOS_validation` forced. The run covered the PM4 ring
fixture, selected draw/resource dumps, synthetic Vulkan readback, R8 upload
reuse, and resolve capability. The log is
[`process2_pm4_interrupt_order_linux_ctest_20261026.log`](../evidence/process2_pm4_interrupt_order_linux_ctest_20261026.log)
(SHA-256 `3d642aab…f9dd6bf7`). Its PM4 draw/resource inputs are synthetic, so
this result does not establish retail gameplay or parity.

## Partial raster state on unresolved PM4 draws (2026-10-28)

For captured indexed draws, the ordered-operation trace now includes decoded
raster state and the raw values of observed guest registers plus a validity
mask. This is retained when decoding is incomplete, so the rejection includes
partial state even when stream validation fails before Vulkan submission. The
stencil reference/write-mask register is printed as valid only if a
corresponding PM4 write was captured.
Linux renderer tests and plugin tests passed 4/4 and 6/6 respectively with
`VK_LAYER_KHRONOS_validation`; the Vulkan minimum remains 1.1. The ARM64
renderer and its check target compile, but no Android device was connected.

This improves diagnosis only. The latest DSO has not yet been replayed against
the retail XEX, so its raw-register output is covered by synthetic regression.
An earlier replay saw unresolved packet 0 with validity mask `0x17038`, but
that build did not include the raw-register formatter. The 14-draw transition
was absent in that replay; EDRAM alias backing and full sequence execution
remain incomplete. See
[`process2_unresolved_draw_partial_registers_20261028.json`](../evidence/process2_unresolved_draw_partial_registers_20261028.json)
for hashes and verification details.
