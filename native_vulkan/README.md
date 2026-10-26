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
