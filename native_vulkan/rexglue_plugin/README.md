# ReXGlue native SHIFT GPU plugin

`rexgpu-shift-native` implements ReXGlue's `IGraphicsSystem` ABI and consumes
the guest PM4 ring without loading the `rexgpu-xenos` renderer. It creates the
SDK's Vulkan presenter with GPU emulation disabled and receives ring updates
through `InitializeRingBuffer` and `CP_RB_WPTR`.

Set `SHIFT_NATIVE_VULKAN_TRACE_RING=1` to emit a bounded ring-contract trace:
each accepted `CP_RB_WPTR`, the worker's `[RPTR, WPTR)` snapshot, and its
consumption plus guest RPTR writeback. The trace stops after 8,192 records and
is disabled by default; it does not change packet parsing or pointer updates.
Use it to correlate a retail guest queue snapshot with the plugin's actual
write-pointer notification and worker state.

The 2026-10-26 Linux diagnostic build passed all three live-ring CTests with
`VK_LAYER_KHRONOS_validation` forced through the loader. Those tests use
synthetic geometry and resources. Their output does not expose the plugin's
`REXLOG` trace sink, so only a retail run with this build can confirm that the
records are emitted and correlate them with the guest WPTR. With the same
synthetic readback fixture, trace-off and trace-on output was byte-identical.
Build hash, commands, scope, and the unresolved P1 pointer observation are
recorded in
[`process2_ring_trace_smoke_20261026.json`](../../evidence/process2_ring_trace_smoke_20261026.json).

The worker keeps the bounded captured register/shader contract, resolves the
captured index, vertex, and tiled texture bytes, translates the observed shader
pair to project GLSL, and compiles that GLSL to Vulkan 1.1 SPIR-V. It batches
supported indexed draws until `PM4_XE_SWAP`, then submits them through the
project-owned Vulkan renderer to the presenter's output image. The renderer
has no XCB or Wayland dependency; only the ReXGlue presenter attaches that
image to a host window.

The supported path is deliberately narrow: captured DMA-indexed triangle-list
draws, AutoIndex point-list draws, and the captured three-vertex AutoIndex
rectangle-list form. Rectangle lists use a project-owned Vulkan geometry stage
to expand each primitive into a two-triangle strip and carry the captured
location-0 interpolator through the generated vertex. The optional
`geometryShader` feature is requested from the Vulkan provider without enabling
GPU emulation; rectangle draws fail closed when the selected device does not
enable that feature. The path also covers the observed vertex shader with no
fetch inputs and its scalar destination relative to the initial `aL` value. The
current control-flow subset rejects loops, so loop-aware relative addressing
remains unsupported. It translates the captured shader pair (including inline
`IM_LOAD_IMMEDIATE`), validates required constants, and resolves supported
vertex and texture resources. Other primitive, shader-interface, raster, and
resource forms are rejected. The captured raster subset includes the Xenos
`PA_SU_SC_MODE_CNTL` front/back cull and front-face bits. Cull-both is rejected
until its retail behavior is captured. The frame path clears the presenter
image and renders the collected draws; it does not reconstruct Xenos EDRAM
contents or read the guest frontbuffer as a finished image. The captured
black texture border has unknown alpha, so transparent-black is still
provisional. Target gamma conversion and the complete retail scene are not
yet verified. To retain useful release-build evidence, the plugin logs the
first 16 distinct decoded-draw rejection reasons and the first 16 distinct
PM4 draw-decode failures at INFO level; rejected draws still fail closed.

## Build and checks

Configure against a ReXGlue SDK checkout that provides the separate
`rexui-vulkan` target:

```sh
cmake -S native_vulkan/rexglue_plugin -B build/rexgpu-shift-native \
  -DSHIFT_REXGLUE_SDK_ROOT=/path/to/rexglue-sdk \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_CXX_FLAGS=-march=x86-64-v2 -DCMAKE_BUILD_TYPE=Release
cmake --build build/rexgpu-shift-native --target rexgpu_shift_native_factory_check
ctest --test-dir build/rexgpu-shift-native --output-on-failure
```

The factory check loads the plugin and verifies ABI and factory rejection
cases. The live-ring smoke creates the SDK presenter, writes a bounded guest
memory fixture, publishes it through `CP_RB_WPTR`, and verifies read-pointer
writeback. It includes the exact captured `DRAW_INDX` packet, captured raster
registers and fetch descriptors, the captured 108-byte PS instruction slice,
and index values from the captured draw. It also includes a synthetic VS,
zeroed constants, and a generated white texture. The worker translates both
shader stages, resolves resources, processes the fixture `DRAW_INDX_2` and
`XE_SWAP`, and asserts that two indexed draws reach the Vulkan presenter and
submit successfully. This is an end-to-end plugin/presenter regression, not a
live retail run or retail image-parity evidence. The DMA draw, shader pairing,
and resource payloads in the fixture are not a new raw retail capture.

The separate `rexgpu_shift_native_live_ring_readback_check` CTest uses the
same synthetic ring with the opt-in magenta pixel shader and output readback.
It requires the presenter image to contain non-black pixels, so it exercises
vertex positioning, rasterization, fragment output, and the presenter readback
path together. On the NVIDIA GeForce GTX 950 host, the 1280x720 readback was
uniform packed magenta (`0xFFF003FF`) across all 921,600 pixels (SHA-256
`bac5569a33a5dbff11ac418a9c89bd18824c1bc0c862420c8da1d7598fc328f2`). This
confirms the synthetic fixture now covers the target; it does not change the
separately captured black retail output or prove retail scene parity.
The readback regression also passed with
`VK_LAYER_KHRONOS_validation` forced through `VK_INSTANCE_LAYERS`; the loader
confirmed the layer was enabled and the run emitted no validation error or
VUID diagnostics.

The platform-independent Vulkan core also has synthetic offscreen AutoIndex
point and rectangle-list draw coverage with no vertex attributes or vertex buffer.
It passed with Vulkan validation on NVIDIA GeForce GTX 950, and on Redmi Note 8
Pro (Mali-G76 MC4) using Vulkan 1.1. Those smoke shaders are synthetic and
verify pipeline/resource/layout operations only; they are not retail output
evidence.

### Existing Android app target

The plugin CMake can be added after an Android host has already added ReXGlue:

```cmake
set(SHIFT_REXGLUE_NATIVE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
add_subdirectory("${SHIFT_NATIVE_PLUGIN_DIR}" shift-native-plugin)
rexglue_setup_target(main GPU_PLUGINS shift-native)
```

Pass `SHIFT_NATIVE_PLUGIN_DIR` from the Android Gradle CMake arguments. The
ReXGlue 0.10.0 Android build has a monolithic `rexui` target, so the plugin uses
its exported Vulkan provider through `rexruntime`. When the SDK header exposes
the optional `with_geometry_shader` factory overload, CMake detects it and
enables that Vulkan feature without GPU emulation; otherwise rectangle draws
fail closed and point draws remain available. The split `rexui-vulkan` target
follows the same feature contract. Debug builds stage
`librexgpu-shift-natived.so`, matching the host plugin loader's debug suffix.

Some Android hosts hardcode the loader ID `xenos` in `OnPreSetup`. For those
hosts, set `SHIFT_NATIVE_ANDROID_XENOS_LOADER_ALIAS=ON`, exclude the SDK's
`rexgpu-xenos` target from the Android build, and stage a copy of
`$<TARGET_FILE:rexgpu-shift-native>` as `$<TARGET_FILE:rexgpu-xenos>` next to
the app library. Do not filter that alias out during Gradle JNI packaging. The
alias file contains the Process 2 Vulkan plugin and exports the same ReXGlue
GPU ABI; it does not contain or call the Xenos renderer. Keep the ordinary
`librexgpu-shift-native.so` as well so hosts that honor the explicit setting
can load it directly. Remove the alias once the app preserves a configured
`gpu_plugin` value and selects `shift-native` explicitly.

The renderer regression matches the captured retail point-raster profile:
4x MSAA, D24S8 with depth/stencil `ALWAYS`, a Y-flipped viewport, full 1280x720
scissor, and blending disabled. It checks the point path and, when geometry
shaders are enabled, synthetic rectangle-list expansion with non-black
readback. It passed on GTX 950 with `VK_LAYER_KHRONOS_validation` and on Redmi
Note 8 Pro (Android API 33, Mali-G76 MC4). These shaders verify Vulkan pipeline
and raster operations; they do not establish live game output or scene parity.

On 2026-10-23, a headless retail Linux run with `--gpu_plugin=shift-native`
mapped this plugin without mapping `rexgpu-xenos`, initialized the guest ring
at `0x09752580`, and consumed 1,828 PM4 packets containing two `XE_SWAP`s. The
ring contained 100 `DRAW_INDX_2` packets: 96 AutoIndex point-list draws and
four three-index AutoIndex rectangle-list draws. No DMA-indexed packet was
observed. The updated plugin submitted two 1280x720 Vulkan frames, each with
24 point-list draws and one rectangle-list draw. Two additional rectangle
draws were rejected, one per swap: their captured target state has
`mode_control=0x00000006` and `color_info=0`, which the supported raster
contract does not accept. This is fail-closed behavior, not a guessed state
mapping. See
[`process2_xbox_live_guest_ring_20261023.json`](../../evidence/process2_xbox_live_guest_ring_20261023.json).
That headless run predates the current copy-state path. The later Android log
records the `mode_control=0x00000006` rectangle as an accepted source-0/sample-0
Copy/Convert to `0x0975e000` at 1280x720. Xenia's Xenos register reference
identifies mode 6 as EDRAM copy, so this packet is a resolve operation rather
than a missing color draw. The phone log and plugin-path evidence are in
[`process2_redmi_note8pro_current_black_output_20261024.txt`](../../evidence/process2_redmi_note8pro_current_black_output_20261024.txt).

On 2026-10-23, the complete Android NFS Shift debug APK was built with
`SHIFT_NATIVE_PLUGIN_DIR` pointing at this plugin and installed on a Redmi Note
8 Pro (Android 13/API 33, Mali-G76 MC4, Vulkan 1.1.131). The Android host's
startup hook selects the loader ID `xenos`, so Gradle stages the Process 2
plugin bytes under both `librexgpu-shift-natived.so` and the loader alias
`librexgpu-xenosd.so`; the two APK entries are identical and contain the Vulkan
plugin, not the Xenos GPU emulator. Runtime logs confirm the emulator-free
Vulkan frontend loaded and consumed the guest PM4 ring. The first build batched
25 draws on the first swap, then rejected a later frame because the batch mixed
1x and 4x-MSAA targets. The captured point draws had a zero color mask and
disabled depth/stencil writes. Process 2 now identifies and elides their
framebuffer effects; the rebuilt APK submits one framebuffer-writing retail
rectangle at each guest swap without the target mismatch. The mode-6 EDRAM
Copy/Convert tuple is decoded for the exact phone capture
(`copy_control=0x00100000`, destination `0x0975e000`, pitch/height 1280x720,
format 6, R/B swap). Process 2 now submits the supported source-0/sample-0
Copy/Convert form as a Vulkan sample-zero pass from its multisample color
attachment into the presenter image. Host and Android offscreen regressions
exercise this conversion, including the captured channel swap. This is a
narrow Vulkan path for the observed tuple; it does not model Xenos EDRAM
accumulation or resolve every guest surface.

A later Linux retail smoke (run 054) captured a separate tiled 1024x512
texture descriptor with Xenos format 19 (DXT2/3) and endian mode 1. The P2
input path now untile-decodes that base-level form and expands its blocks to
RGBA8 on the CPU before Vulkan upload, so Android does not depend on optional
BC texture-compression support. The regression covers the captured descriptor
and tiling/endian/decode rules, and also ran on ARM64; it does not prove the
real guest texture has produced a visible retail draw. A later bounded retail
smoke (run 058) confirmed that the real #28 guest bytes pass this DXT2/3 path
and enter the Vulkan draw batch; that run did not include an image readback.

Run 058 also captured draw #27 with target pitch 1280, viewport `x=392..888,
y=478..486`, and a matching window scissor. The renderer now retains the full
1280x720 target extent from the preceding guest swap and passes the captured
496x8 viewport and scissor through Vulkan. The exact register tuple is covered
by host and ARM64 offscreen regressions, including a check that test pixels
stay inside the captured scissor. Bounded retail run 059 no longer reports
#27 as unresolved, although it did not include pixel readback. Draw #29's
target/raster and Copy/Convert state remain unresolved.

The latest Android debug APK
(`ff5c30af24013b315280e161cd383c4cd50874a1e096f0d0383364f004a311c6`) was
installed on the Redmi Note 8 Pro. The current runtime log `nfs_shift_031.log`
confirms one retail draw submitted at each of two guest swaps and the
1280x720 Copy/Convert destination matching the swap address. The first Vulkan presenter readback is
still all black (zero non-black pixels, FNV-1a `B161DE6EEC272325`), and the
device screenshot remains black. No later PM4 draw batch was observed after
startup. Android A/Start events from the default keyboard source, a virtual
Xbox 360 controller created with `/dev/uinput`, and a default-keyboard Enter
event left the foreground process, runtime log, screenshot, and PM4 output
unchanged. In a follow-up check, Android InputReader registered the virtual
controller as `GAMEPAD | JOYSTICK`; a two-second `BTN_START` press still did
not advance the process or produce another PM4 batch. A separate two-second
`BTN_SOUTH`/Android `BUTTON_A` press had the same result. Direct `sendevent`
injection into the phone's built-in `uinput-fpc` device is denied, and no
physical controller was attached. The observations are recorded in the
[`android_xbox_key_input_check_20261024`](../../evidence/process2_xbox_live_guest_ring_20261023.json)
evidence entry. This means visible retail output is not ready or verified; the
successful synthetic Vulkan regression only validates the sample-zero
conversion path. See
[`process2_xbox_live_guest_ring_20261023.json`](../../evidence/process2_xbox_live_guest_ring_20261023.json)
and [`process2_redmi_note8pro_current_black_output_20261024.txt`](../../evidence/process2_redmi_note8pro_current_black_output_20261024.txt)
for build and device evidence. The game package and plugin are integrated on
Android, but visible retail output and scene parity are not verified. The
`xenos` loader alias can be removed when the host preserves an explicit
`gpu_plugin=shift-native` setting.

Two Android CPU probes show main/SDL threads busy while the Vulkan PM4 worker
is idle. The latest sample at 02:13:12 MSK reported `Core 0/0: Main` at
85–102%, `SDLThread` at 70.5–85%, and `SHIFT Native GP` at 0% across two
samples. The foreground app remained on the same two startup swaps; its log
still ends at RPTR `0x49`, and the fresh screenshot stayed black with the same
hash. This is consistent with a runtime-side progress loop while the renderer
has no new commands; it does not identify the exact guest function or prove
the cause. Guest execution and scheduling remain Process 1 ownership. The
full sample is recorded in
[`process2_redmi_note8pro_guest_cpu_probe_20261024.txt`](../../evidence/process2_redmi_note8pro_guest_cpu_probe_20261024.txt)
and [`process2_redmi_note8pro_guest_cpu_probe_20261024_later.txt`](../../evidence/process2_redmi_note8pro_guest_cpu_probe_20261024_later.txt).

A one-time Android debug diagnostic forced the fragment shader to magenta while
leaving the captured retail vertex shader, geometry, draw, and Copy/Convert
path intact. On the Redmi Note 8 Pro it produced 518,400 non-black pixels in
the Vulkan guest-output readback (FNV-1a `DA74DA070BC0D725`) and a visible
magenta region in the [device screenshot](../../evidence/process2_redmi_note8pro_android_vulkan_magenta_diagnostic_20261023.png).
This confirms that the Android Vulkan presenter displays the submitted retail
rectangle geometry. The magenta output is synthetic diagnostic color, not
retail pixel evidence or scene parity. The original APK was restored and is
running; with the captured retail pixel shader, its startup readback remains
fully black. The temporary override was removed from the working tree.

A follow-up Android run logged the guest read-pointer writeback contract without
changing fragment output. `VdEnableRingBufferRPtrWriteBack` passed
`0x17AF403C`; the plugin translated it to `0x217af403c`, then wrote and read
back `0x19`, `0x1F`, and `0x49`. The run still had only two startup swaps and a
black retail readback (zero non-black pixels, FNV-1a
`B161DE6EEC272325`). A later Process 1 Linux/GDB probe confirmed the same
`VdEnableRingBufferRPtrWriteBack` argument (`0x17AF403C`) and translated host
address (`0x217af403c`). It identified the previously reported `0xB7AF4000`
as the ring base, not the RPTR writeback destination, and observed writes at
the correct destination. Its final snapshot included the guest queue-polling
frame and GDB then killed the inferior; this does not prove an independent
guest deadlock or later game progression. This closes the address discrepancy
but does not establish retail output. The original APK was
restored and left foregrounded; during the next 45 seconds it produced no
further PM4 batches or swaps and stayed black. See
[`process2_redmi_note8pro_rptr_writeback_20261023.txt`](../../evidence/process2_redmi_note8pro_rptr_writeback_20261023.txt)
and [`process2_linux_rptr_crosscheck_20261024.txt`](../../evidence/process2_linux_rptr_crosscheck_20261024.txt),
plus the `android_rptr_writeback_diagnostic_20261023` and
`linux_rptr_crosscheck_20261024` evidence objects.

The optional `SHIFT_NATIVE_VULKAN_READBACK_PATH` captures the first successful
presenter image as `VK_FORMAT_A2B10G10R10_UNORM_PACK32`. With the opt-in
`SHIFT_NATIVE_VULKAN_DEBUG_FRAGMENT_COLOR=magenta` override, the live retail
draws produced 518,400 non-black pixels in the 1280x720 readback (FNV-1a
`DA74DA070BC0D725`, raw SHA-256
`21d2868e9e0b91638d96e30dfe446a4748ef217efaa09e10ed179697e95e35e8`). This
confirms the captured live geometry reached rasterization and the Vulkan
presenter; the replacement pixel shader makes this diagnostic output
synthetic. The [decoded readback](../../evidence/process2_xbox_live_vulkan_magenta_raster_diagnostic_20261023.png)
shows the magenta rasterized region over the black clear. With the captured
retail pixel shader restored, the readback had
zero non-black pixels (FNV-1a `B161DE6EEC272325`, raw SHA-256
`cd6226f8bf299d3ab51cfc10af0b585167106d7caa356e8604bfe48ad9a49de5`). A
shader/input diagnostic recorded a 36-byte pixel shader that forwards its
interpolator and a sample vertex whose location-1 value was `(0, 0, 0, 0)`.
That is consistent with the black early-startup image, but does not prove later
gameplay output or explain every skipped draw. The current retail window also
remained black apart from the host cursor. These runs confirm live Vulkan draw
submission and rectangle expansion; they do not demonstrate visible retail
content or scene parity. Full Xenos EDRAM accumulation, other copy and
raster/resource states, later gameplay output, and Vulkan validation for a live
retail frame remain unverified.

The first 73-packet startup batch contains 24 point draws before the captured
vertex-shader control register is available, so those draws are skipped. Later
ring batches provide the required state and submit the supported draws. This
ordering is preserved in the logs rather than hidden by synthesized defaults.

The earlier one-draw capture bundle remains separate evidence for the project
renderer, not proof of a complete scene.

The repository also builds a minimal Android NativeActivity surface probe,
separate from the complete Android app integration above. The Android arm64 CI builds
the project Vulkan renderer smoke and publishes its executable plus Vulkan 1.1
SPIR-V inputs. The earlier artifact from
[CI run 39938067570](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/actions/runs/39938067570)
passed the original renderer smoke on this phone. For the readback update, we
rebuilt the test locally for Android arm64 and ran it on the connected Redmi
Note 8 Pro (Android API 33, Mali-G76 MC4):
`synthetic offscreen Vulkan 1.1 AutoIndex point draw and output readback passed
on Mali-G76 MC4`. The updated conversion regression reports that the captured
sample-zero Copy/Convert path passed on Mali-G76 MC4. These device tests use
synthetic draws and ran without the
validation layer; they do not show a retail frame. Temporary device files were
removed. The parser, guest-ring, shader-translation, and renderer checks were
also rebuilt for API 33 and rerun on the device.

A fresh build from the current Process 2 checkout (`699b38a7`) used NDK
r28.2 with `ANDROID_ABI=arm64-v8a` and `ANDROID_PLATFORM=android-29`. On
2026-10-23, `shift_xbox_draw_input_check`, `shift_xbox_guest_ring_check`,
`shift_xbox_shader_translate_check`, and
`xbox_live_vulkan_renderer_check` all exited successfully on the connected
Redmi Note 8 Pro (Android API 33, Mali-G76 MC4). The renderer check submitted
its synthetic Vulkan 1.1 AutoIndex point draw and verified output readback.
This earlier current-source device run covered the ARM64 parser, translator,
and project renderer core before the complete Android app integration; it did
not load the ReXGlue plugin or run the retail guest ring.

Using the same NDK/API29 configuration, the current
`shift_native_gpu_plugin.cpp` translation unit also compiled by itself for
`aarch64-none-linux-android29` (exit 0). This isolates the renderer-owned
plugin source from the full SDK link. Clang emitted one non-fatal warning in
the SDK header `rex/platform/fpscr.h` about the ARM64 `fpcr` inline-assembly
operand width. This was a translation-unit compile only; the later Gradle build
above links and runs the plugin in the complete Android app.

The guest-ring path now decodes the captured `PM4_INTERRUPT` CPU mask and
dispatches the registered GPU callback through a ReXGlue `XHostThread`, so the
callback has a guest thread context. The callback is issued after the current
ring batch is consumed and its read pointer is published; exact ordering at
each interrupt packet inside a batch is not verified. The decoder regression
and Android API 33 guest-ring smoke passed on Redmi Note 8 Pro (Mali-G76 MC4),
and the Linux plugin suite passed 3/3 with the readback regression also passing
under Vulkan validation. Those earlier checks preceded the complete Android
game integration; a fresh host CTest run after that integration passed 4/4.
The current-source Linux rerun described above also consumed the captured
interrupts and dispatched callbacks. See the
`gpu_interrupt_routing_update` and `post_scalar_destination_live_rerun` entries
in the evidence JSON for the build and test details.

On 2026-10-24, a fresh ADB screenshot of the still-running Redmi Note 8 Pro app
was fully black. Its latest runtime log records one captured retail draw
translated and submitted to the Vulkan presenter, but the
`VK_FORMAT_A2B10G10R10_UNORM_PACK32` readback has zero non-black pixels
(`B161DE6EEC272325`). This confirms the guest draw reaches Vulkan while visible
retail output remains unverified. A separate live Linux diagnostic of this
captured shader pair recorded vertex input location 1 as `(0,0,0,0)`; the
vertex shader forwards it to the pixel shader, which forwards it to color.
That is consistent with the black result for this early captured draw, but does not prove
later shaders or frames. The mode-6 rectangle is accepted through the
source-0/sample-0 Copy/Convert path. The magenta path and other synthetic
readbacks are diagnostics only. See
[`process2_redmi_note8pro_current_black_output_20261024.txt`](../../evidence/process2_redmi_note8pro_current_black_output_20261024.txt)
for device identity, screenshot/log hashes, and batch details.

The 2026-10-24 follow-up added the missing periodic guest source-0/VBlank
callback (60 Hz on a ReXGlue host thread) and reports MMIO interrupt-status
register `0x1951` bit 0 as asserted. A rebuilt full Android APK loaded this
path on the Redmi Note 8 Pro: its log records three VBlank callbacks, two
source-1 PM4 callbacks, RPTR progress through 25/31/73, two guest swaps, and
two Vulkan frame submissions. The guest still produced no later PM4
batches during the next 2m50s; screenshot and readback stayed black (zero
non-black pixels, FNV-1a `B161DE6EEC272325`). Thus VBlank delivery and Vulkan
submission are verified, but visible retail output is not. The current-source
host live-ring executable and synthetic magenta readback both passed directly;
the latter loaded `VK_LAYER_KHRONOS_validation` and emitted no VUID. See
[`process2_redmi_note8pro_vblank_probe_20261024.json`](../../evidence/process2_redmi_note8pro_vblank_probe_20261024.json)
for APK hashes and the bounded runtime evidence.

The 2026-10-24 Linux ring-worker follow-up writes the same fixture as three
separate CP_RB_WPTR MMIO updates, waiting for RPTR after each one. All three
batches were consumed and each produced a Vulkan presenter submission, both
with and without `VK_LAYER_KHRONOS_validation`; validation reported no VUIDs.
This rules out a worker that permanently stops after its first batch when the
guest provides more work. It does not explain why the retail guest stops
writing WPTR after its startup work. The fixture uses synthetic geometry and
resources, and the Redmi Note 8 Pro still has a black screenshot and readback,
so this regression is transport evidence only, not retail-output evidence.
The callback ABI review also confirms that the plugin forwards the registered
guest `user_data` unchanged. See
[`process2_ring_worker_three_batch_regression_20261024.json`](../../evidence/process2_ring_worker_three_batch_regression_20261024.json)
and its validation log for hashes and details.

A Linux retail run on 2026-10-24 also produced a complete 1280x720 Vulkan
readback: all 921,600 RGB pixels were black (packed-word histogram
`0x00000000`: 518,400; `0xC0000000`: 403,200; FNV-1a64
`B161DE6EEC272325`). The log records 232 one-draw submissions and 341 frame
refresh failures in the bounded run. Submission counts do not establish visible
output. A separate diagnostic replaced only the pixel shader with magenta while
retaining the captured retail vertex shader, inputs, raster state, and draw. It
produced 518,400 magenta pixels in a complete 1280x720 readback, confirming
coverage and presenter readback for this draw; it does not verify the retail
pixel shader. A prior attempt with another output path failed to save and is
excluded. See
[`process2_linux_retail_black_output_20261024.json`](../../evidence/process2_linux_retail_black_output_20261024.json).
The lineage-verified 30-second follow-up used the exact staged host executable
and alpha-blend plugin and produced the identical black readback hash
(`cd6226f8...`); it logged 813 multi-draw refresh failures. This confirms the
blend-state fix did not change the startup image. An earlier 15-second retest
used a different host executable and is excluded from source-lineage evidence.
Renderer validation now reports the failing draw index and sample or scissor
values instead of a generic target/scissor error. Synthetic host regressions
cover the sample and scissor diagnostics; the updated plugin still needs a
retail run to identify which live draw condition is rejecting those frames.
An exact-executable/plugin magenta control also produced 518,400 non-black
pixels with zero refresh failures, but logged only two one-draw submissions.
It confirms that diagnostic output reaches readback; it does not replay the
retail multi-draw sequence and therefore cannot identify or validate its fix.

On 2026-10-24, the Android ARM64 plugin added a Vulkan pass transition for the
captured `[4x-MSAA, 1x, 1x]` retail frame and a single-sample source-0/sample-0
Copy/Convert shader. The existing Android app then displayed the original NFS
SHIFT logo on the Redmi Note 8 Pro; the screenshot and runtime/APK/plugin hashes
are recorded in
[`process2_redmi_note8pro_vulkan_retail_logo_20261024.json`](../../evidence/process2_redmi_note8pro_vulkan_retail_logo_20261024.json).
The earlier first-swap debug readback remains black because it was taken before
the textured draws. A later screenshot from the same run returned to black as
the splash ended. The runtime also reports missing guest files such as
`menu_background.xml`; this is consistent with, but does not prove the cause
of, the post-splash black screen. This verifies the first original retail
pixels through the project Vulkan path, not menu, race-scene, or full-game
parity. The host regression suite passes 4/4, including the mixed-sample path
under Vulkan validation.

To correlate a specific Android startup draw batch with Vulkan output, set the
plugin CMake cache variable `SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME` to its
submitted-frame number (default `500`). Set the optional
`SHIFT_NATIVE_VULKAN_DEBUG_READBACK_PATH` CMake cache variable to save that
frame's raw output. A frame-4 ARM64 debug build read back 53,098 non-black
pixels (`915336228EB84E49`) from a batch containing the captured 1024x256 retail
texture and original guest shader pair, without the synthetic fragment
override. The saved 1280x720 `VK_FORMAT_A2B10G10R10_UNORM_PACK32` Vulkan image
decodes to the SHIFT title logo; the device screenshot about seven seconds
later shows the same logo. A later screenshot is black. This confirms the
first retail textured output, not sustained menu or race rendering. See
[`process2_redmi_note8pro_vulkan_frame4_pixels_20261024.json`](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.json),
its [device screenshot](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.png),
the [decoded Vulkan image](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_decoded_20261024.png),
the [raw readback](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.bin),
and [full device log](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.log).
For targeted smoke tests, setting the runtime environment variable
`SHIFT_NATIVE_VULKAN_READBACK_PATH` captures a submitted Vulkan output frame.
`SHIFT_NATIVE_VULKAN_READBACK_FRAME` optionally selects its one-based presenter
frame number; when omitted with an explicit path, frame 1 is captured. The
configured Android debug fallback path still uses its compile-time selected
frame.

The latest bounded Linux retail run (060) submitted 1,349 presenter frames and
accepted 1,349 Copy/Convert operations with no Vulkan refresh failures. Its
frame-1 readback is all black (1280x720 A2B10G10R10, SHA-256
`cd6226f8bf299d3ab51cfc10af0b585167106d7caa356e8604bfe48ad9a49de5`). Draws
#25 and #29 captured Xenos EDRAM mode 5. The current decoder now treats that
observed mode as depth-only and disables Vulkan color writes, with the exact
register tuple covered by host and Mali-G76 offscreen regressions. This is
state support, not evidence that those draws produce visible color. Draw #0
still arrives without surface, viewport, or blend registers (`valid_mask`
`0x17038`), so it remains fail-closed. A bounded retail readback of submitted
frame 100 with the current plugin is pending; sustained menu/race output
remains unverified.

## Bink cutscene draw follow-up (2026-10-25)

Retail presenter frame 400 captured draw #2614 as a full-screen Bink YUV rectangle: four vertices spanning `(0,0)` to `(1280,720)`, three R8 planes (1280x720 luma and two 640x360 chroma planes), `clip_disabled=1`, and `PA_CL_VTE_CNTL=0x400`. The old window-coordinate classifier also required `VTE_XY_FMT`, so it left `window_xy=0`; the readback consequently covered only `[640,0]..[1279,359]` and its RGB channels peaked at 4/1023. The parser now derives window-coordinate mode from clip-disable itself, while VTE scale and offset flags still independently select the captured viewport terms. The Vulkan vertex path maps those window coordinates into NDC and uses the complete positive viewport.

A captured-data replay compiled the logged Bink shader translations for Vulkan 1.1, applied the same window-to-NDC transform, and submitted the captured constants, raster state, geometry, and raw texture planes to the project Vulkan renderer. On the GTX 950 with validation enabled it covered the full 1280x720 frame (921,528 nonzero pixels; bounding box `[0,0]..[1279,719]`) with zero validation errors. Compared with the captured YUV conversion formula, mean absolute error was 0.09/0.05/0.09 per 10-bit channel; differences are from linear chroma filtering. The replay shows the EA intro mark and validates this captured draw path, not a live post-fix game launch. Inputs and output binaries remain outside Git; hashes and the replay method are in [`process2_linux_bink_cutscene_replay_20261025.json`](../../evidence/process2_linux_bink_cutscene_replay_20261025.json).

The earlier headless launch after the fix stopped submitting draws after presenter frame 352 and did not produce a live Bink readback. A fresh isolated Linux retail launch with the current P2 plugin then captured presenter frame 400 from the live game. The 1280x720 Vulkan readback displays the full EA intro mark across the complete target; its bounding box is `[0,0]..[1279,719]`, with 921,173 non-black RGB pixels. The visible image and readback hashes are recorded in [`process2_linux_bink_cutscene_live_frame400_20261025.json`](../../evidence/process2_linux_bink_cutscene_live_frame400_20261025.json) and [the decoded frame](../../evidence/process2_linux_bink_cutscene_live_frame400_20261025.png). This is original live retail output with the captured shader path, not synthetic fragment color.

That launch submitted 765 Vulkan frames and accepted 765 matching Copy/Convert operations. Its last submission was at 11:42:42.676 MSK; at 11:45:30 MSK the process was still alive, the guest main thread was running, and the native GPU worker was waiting for more work. No further submission appeared for 167 seconds. This confirms the captured Bink draw is no longer clipped or black in the live Vulkan path, but does not confirm the cutscene-to-menu transition. The remaining stop occurs after renderer submission has gone idle; its exact guest/runtime cause is unproven and remains outside Process 2 ownership. The live launch did not force the Vulkan validation layer; the independent Vulkan 1.1 Bink replay still has zero validation errors, and the current Linux plugin suite passes 4/4.

A fresh Android API 26 / arm64-v8a configuration against the depth/stencil-resolve SDK branch enables the P2 provider overload. The P2 plugin translation unit and the SDK Vulkan provider/device translation units compile for ARM64. Building the full Android consumer then stops in the existing ReXGlue `src/core/fiber_posix.cpp`: Bionic does not declare `getcontext`, `makecontext`, or `swapcontext`. That runtime-owned Android fiber gap prevents rebuilding the APK with the enabled resolve capability; P2 did not modify runtime or scheduler code. The observed phone trace fails at the earlier mixed 4x-to-1x depth/stencil frame, so the cutscene's live transition remains blocked pending an Android-compatible runtime build and a new device run. Detailed compile evidence is in [`process2_provider_resolve_integration_20261024.json`](../../evidence/process2_provider_resolve_integration_20261024.json).

## Language selector text and shader interpolators (2026-10-25)

The retail language selector rendered its rows and highlight but omitted all text. The font pixel shader samples atlas UVs from a nonzero Xenos interpolator register; the translator had routed every vertex interpolator export to Vulkan location 0 and initialized only pixel register `r[0]`. Vertex exports now preserve their Xenos destination index across Vulkan locations 0–15, and pixel `r[]` inputs read the matching location. The rectangle-list geometry shader forwards the same 16 locations so that this stage does not break the vertex-to-pixel interface.

The before/after images are 1280x720 outputs from the retail Xbox 360 title (title ID `454108B4`) through the project's native Vulkan presenter on a Linux host with an NVIDIA GTX 950. Before, the six language rows were blank; after the translator change, the original retail draw stream displays `English`, `Français`, `Italiano`, `Deutsch`, `Español`, and `Nederlands`. These captures contain the game's output; no synthetic shader color was used. See [`process2_linux_language_menu_20261025.json`](../../evidence/process2_linux_language_menu_20261025.json), [before](../../evidence/process2_linux_language_menu_before_20261025.png), and [after](../../evidence/process2_linux_language_menu_after_20261025.png).

The captured frame-150 label draws use topology 0; two preceding UI draws use topology 2. The visual after-capture was taken after the varying-index translator fix and before the follow-up geometry-stage pass-through change. A later frame-150 run with the final plugin and `VK_LAYER_KHRONOS_validation` produced no VUIDs but was entirely black, so it validates the corrected stage interface without serving as a second visual menu capture. Both the native Vulkan 4-test suite and the P2 plugin 4-test suite pass with the validation layer enabled.

A fresh ARM64 P2 plugin was installed and run on Redmi Note 8 Pro. It renders the retail SHIFT loading screen with the yellow-orange progress bar, then the Android Vulkan provider rejects the 24-draw 4x-to-1x depth/stencil frame because the package's SDK does not expose the optional `with_depth_stencil_resolve` capability. That earlier snapshot remained black and did not capture the language selector. See [`process2_redmi_note8pro_language_menu_android_20261025.json`](../../evidence/process2_redmi_note8pro_language_menu_android_20261025.json) for that bounded capture; its result does not describe the later state of the same running process.

## Redmi Note 8 Pro language selector follow-up (2026-10-25)

The user observed the language menu between Loading and the EA intro, with its labels missing. The installed APK contains the P2 plugin built with the interpolator-location fix above, and its runtime shader log shows matching GLSL locations 0–15. The retail `Loading...` draw is visible and samples the same format-19 font atlas at `0x09E57000`; this verifies the basic atlas path but does not prove the selector's own draw state and shader constants.

The device log records eight rejected refreshes, each with 24 captured draws, from 12:53:53 to 12:53:58 MSK. The provider reports that 4x-to-1x depth/stencil preservation needs its optional resolve capability, which this installed runtime does not enable. The log does not identify those frames as the selector or establish that this failure caused the missing labels. The same process later resumed 4-draw Vulkan frames and read back frame 500 with 921,274 non-black pixels; later screen capture matched the retail `Franchise_Ident.bik` asset. The language labels on Mali remain unverified.

The follow-up log, current screen, and short recording are in [`process2_redmi_note8pro_language_menu_followup_android_20261025.json`](../../evidence/process2_redmi_note8pro_language_menu_followup_android_20261025.json), [`the log`](../../evidence/process2_redmi_note8pro_language_menu_followup_android_20261025.log.gz), [the current screen](../../evidence/process2_redmi_note8pro_after_language_menu_android_20261025.png), and [the recording](../../evidence/process2_redmi_note8pro_ea_mark_sequence_android_20261025.mp4). The next verification needs a targeted language-menu capture after integrating the provider depth/stencil-resolve capability into an Android-compatible runtime build. No Process 1 source files were changed.

## Redmi Note 8 Pro Bink playback match and rate (2026-10-25)

A later phone screenshot and 10-second recording show the NFS SHIFT title over the pink background. The `Franchise_Ident.bik` file on the phone and the local retail game data have the same SHA-256 (`34a9ffeb18fb8410f7857e9abff361888050677f166aad3834a3a4125595cd1c`). The retail file probes as 1280x720 Bink video, 9.376 seconds long. Downscaled grayscale phone frames correlate with source frame 13 of `Franchise_Ident.bik` at 0.7735–0.8102; `NFS_SHIFT_DDAY.bik` and `NFS_SHIFT_TestLap.bik` peak at 0.4326 and 0.2364 respectively. This identifies the phone output as the original franchise-ident video sequence, not a synthetic renderer image.

The live log still shows only 57 submitted four-draw frames in one minute (about 0.95 submissions per second). A one-shot Android CPU sample reported 672% process CPU, distributed across the native GPU worker, guest main/controller threads, and audio. The renderer is presenting the real video, but this capture is far below real-time speed and does not establish a playable game. Screenshot, recording, input hashes, and comparison method are in [`process2_redmi_note8pro_franchise_ident_android_20261025.json`](../../evidence/process2_redmi_note8pro_franchise_ident_android_20261025.json), [the phone screenshot](../../evidence/process2_redmi_note8pro_franchise_ident_android_20261025.png), and [the screen recording](../../evidence/process2_redmi_note8pro_franchise_ident_android_20261025.mp4). Language-menu labels remain unverified on Mali.

## Cutscene pipeline-cache follow-up (2026-10-25)

The live submit path called `vkCreateGraphicsPipelines` with `VK_NULL_HANDLE` for every captured draw on every frame. The renderer now accepts an optional caller-owned `VkPipelineCache`; the native plugin creates one for its Vulkan device, reuses it across submissions, and destroys it after the GPU worker stops and before the provider is released. The native renderer regression submits the same captured-data test frame twice through that cache and compares full readbacks byte-for-byte. This checks cache reuse preserves output; it is a synthetic renderer regression, not retail parity or a performance benchmark.

The complete native Vulkan suite passes 4/4 on the GTX 950; the renderer regression reports Vulkan validation enabled and zero validation errors. The current Process 2 `rexui-vulkan` plugin build and its factory/live-ring/readback checks pass 3/3. The updated plugin translation unit also compiles for Android API 26 / ARM64 against the resolve-capable SDK branch. At that point each frame still created and destroyed its draw resources and waited for `vkQueueWaitIdle`; the bounded in-flight follow-up below removes that queue-wide wait for cached, no-readback submissions.

## Bink plane upload reduction (2026-10-25)

An 8-second `simpleperf` sample of the running Redmi EA intro found 54.83% of GPU-worker samples on the `submit_mixed_sample_copy_frame` path. Within draw preparation, the call graph attributes 96.83% to `untile_captured_texture_2d`; its vector allocation and initialization were prominent. The saved screenshot shows the original EA SHIFT mark. The sampled APK predates this optimization, so these numbers are a baseline, not a before/after result.

Retail Bink draw #2614 uses linear format-2 R8 planes with descriptor swizzle `0xA00`, decoded as `[X,X,X,One]`. The plugin now preserves only that exact unsigned, non-endian-converted layout as `VK_FORMAT_R8_UNORM`; all other texture layouts retain the existing RGBA8 conversion path. Native R8 sampling followed by the captured swizzle produces the same replicated RGB and alpha-one values as the previous expanded texture. The path also stops copying the first plane into an unused legacy RGBA field when the multi-plane list is present. For the captured 1280x720 luma plus two 640x360 chroma planes, image upload payload falls from 5,529,600 to 1,382,400 bytes per draw, with another 3,686,400-byte legacy luma copy removed.

Host renderer, plugin, Android renderer-target, and Android ARM64 plugin-translation-unit checks pass. The Android CMake target now generates the two clip-disabled window-coordinate SPIR-V inputs required by the renderer regression. The synthetic offscreen renderer check also ran directly on the Redmi Mali-G76 MC4 and passed its mixed R8/RGBA8 draw, raster, depth/stencil SAMPLE_ZERO, and Copy/Convert checks. A full Android ARM64 APK was then built with the current P2 plugin and verified: both `librexgpu-shift-natived.so` and the loader alias `librexgpu-xenosd.so` contain the same stripped plugin bytes and matching ELF build ID. The candidate has not been installed on the phone because the existing game session is active; no live performance gain or cutscene completion is claimed. The running phone screen still showed the EA intro during the build ([capture](../../evidence/process2_redmi_active_intro_during_apk_build_20261025.png)). This APK uses the v0.10.0 provider without optional depth/stencil resolve, so that earlier selector limitation remains. Build/package hashes and constraints are in [`process2_android_apk_build_20261025.json`](../../evidence/process2_android_apk_build_20261025.json); R8 profile, exact guard, byte calculation, and device renderer test are in [`process2_redmi_cutscene_r8_upload_followup_20261025.json`](../../evidence/process2_redmi_cutscene_r8_upload_followup_20261025.json), with the baseline screen [saved here](../../evidence/process2_redmi_cutscene_profile_screen_20261025.png).

## Bink R8 row-copy follow-up (2026-10-25)

The same retail draw #2614 capture reports tight R8 planes: 1280x720 luma at 921,600 bytes and two 640x360 chroma planes at 276,480 bytes each. `copy_captured_r8_texture_2d` now resizes the destination once and copies a tight plane with one `memcpy`; padded rows still use bounded per-row copies. For this captured layout that replaces 1,440 row-wise vector inserts with three bulk copies while preserving the same bytes and R8 sampling contract. Host CTest passes 4/4 with `VK_LAYER_KHRONOS_validation` enabled; the Android API 26 ARM64 draw-input regression also ran successfully on the Redmi while the game remained alive at PID 6314. This validates the texture-copy contract, not a live FPS gain: Android `simpleperf` could not open perf events, and the active APK predates this change. Evidence and limits are in [`process2_bink_r8_row_copy_followup_20261025.json`](../../evidence/process2_bink_r8_row_copy_followup_20261025.json).

## Redmi Bink playback progression sample (2026-10-25)

Three time-separated phone captures correlate with frames from the retail `Franchise_Ident.bik`: the best 10-fps source matches are approximately 4.9 s, 5.1 s, and 7.7 s, with grayscale correlations 0.907, 0.997, and 0.998. Over 101.905 seconds of wall time, the source advances about 2.8 seconds (roughly 2.7% of real time). This confirms original Bink content is reaching the display through the running Vulkan game, while its very slow progression still blocks the startup sequence. A one-shot thread snapshot shows the native GPU worker around 116% CPU, with the guest main and two controller threads also around 103–116%; it does not isolate the cause. The installed APK predates the latest R8 changes, so this is not an after-change measurement. Source matching, screenshots, thread snapshot, and precision limits are recorded in [`process2_redmi_franchise_ident_progress_20261025.json`](../../evidence/process2_redmi_franchise_ident_progress_20261025.json), with the [first](../../evidence/process2_redmi_franchise_ident_frame_a_20261025.png), [second](../../evidence/process2_redmi_franchise_ident_frame_b_20261025.png), and [third](../../evidence/process2_redmi_franchise_ident_frame_c_20261025.png) phone captures.

A new Android ARM64 debug APK was built from the latest Process 2 source with the row-copy fast path. Package signature verification passed, and both packaged loader names contain byte-identical current P2 plugin code with the same ELF build ID. The candidate remains uninstalled because PID 6314 is an active game session. The provider in this package still lacks the optional depth/stencil resolve capability; no live speedup or cutscene completion is claimed. APK hashes and package checks are in [`process2_android_r8_bulk_copy_apk_20261025.json`](../../evidence/process2_android_r8_bulk_copy_apk_20261025.json).

## Redmi Franchise_Ident loop observation (2026-10-25)

Two additional phone captures 98.258 seconds apart match the same retail `Franchise_Ident.bik` near source times 8.0 s and 1.6 s (correlations 0.99848 and 0.99963). With the 9.376-second file duration, this is a source-time wrap and an estimated 3.0% playback rate. The phone remained on the original fullscreen video across the interval; the sample does not establish whether game flow expects input or why the guest has not left this screen. PID 6314 remained active and the APK was not updated. Capture hashes and matching limitations are in [`process2_redmi_franchise_ident_loop_20261025.json`](../../evidence/process2_redmi_franchise_ident_loop_20261025.json), with the [pre-wrap](../../evidence/process2_redmi_franchise_ident_loop_before_20261025.png) and [post-wrap](../../evidence/process2_redmi_franchise_ident_loop_after_20261025.png) captures.

## Redmi live cutscene progress follow-up (2026-10-25)

Two further captures of the active phone session match source positions 0.7 s and 4.3 s in the retail `Franchise_Ident.bik`, 86.563 seconds apart, at correlations 0.85931 and 0.91819. The video is advancing through the native Vulkan output at about 4.2% of its source rate, so the startup sequence remains on the intro video in this sample. The installed app still predates the native R8 plane and row-copy changes; the 4.2% observation is a baseline, not an after-change result. No install or restart was performed. The matching method, hashes, limits, and [first](../../evidence/process2_redmi_cutscene_progress_e_20261025.png) / [second](../../evidence/process2_redmi_cutscene_progress_f_20261025.png) captures are recorded in [`process2_redmi_cutscene_progress_followup_20261025.json`](../../evidence/process2_redmi_cutscene_progress_followup_20261025.json).

## Redmi Note 8 Pro captured Bink draw replay (2026-10-25)

The captured retail Bink draw #2614 was replayed offscreen on the Redmi Note 8 Pro Mali-G76 MC4 using the actual translated shaders, constants, rectangle geometry, and three R8 planes. The output contains the original EA SHIFT mark and is bitwise-identical across two Mali readbacks; compared with the GTX 950 host output, each 10-bit RGB channel differs by at most two levels. The eight warmed Mali submissions averaged 13.1 ms. Android has no `VK_LAYER_KHRONOS_validation`, so validation was enabled only on the host. This isolates one single-sample draw: it bypasses guest/Bink decode and Copy/Convert and does not replay the mixed-sample frame or measure full-game speed. The game remained active at PID 6314. Details and the [Mali readback image](../../evidence/process2_redmi_bink_retail_draw_replay_20261025.png) are in [`the evidence record`](../../evidence/process2_redmi_bink_retail_draw_replay_20261025.json); language-selector labels remain unverified by this replay.

## Bink R8 resource reuse follow-up (2026-10-25)

The live renderer now retains a bounded set of `VK_FORMAT_R8_UNORM` images and persistently mapped upload buffers for recurring `(draw slot, fetch constant, extent)` plane slots. Each submission still copies the latest captured bytes into the upload buffer and flushes non-coherent memory; the image transitions back from shader-read before the next transfer. The cache is capped at 16 MiB and evicts entries unused for 120 submitted frames. RGBA8 inputs and R8 resources that do not fit remain on the existing per-submit allocation path. The provider clears the cache after its worker stops and before destroying its Vulkan device.

The renderer regression changes an R8 plane between submissions and checks that the cached output matches a fresh allocation and differs from the prior frame. Linux native Vulkan CTest passes 4/4 with `VK_LAYER_KHRONOS_validation`; the Linux P2 plugin suite passes 4/4. The ARM64 renderer and plugin translation unit compile, and the standalone synthetic offscreen renderer check passes on the Redmi Note 8 Pro Mali-G76 MC4. The synthetic check is not retail Bink parity. The resolve-enabled SDK branch still fails in its Android runtime at `fiber_posix.cpp` (`getcontext`/`makecontext`/`swapcontext`) and `memory_posix.cpp` (`GetAndroidApiLevel`), outside Process 2. Using the existing v0.10.0 Android SDK, the current P2 plugin linked into a signed ARM64 APK. That APK was installed and launched on the Redmi; its provider does not expose the optional depth/stencil resolve capability. The live Bink observation and subsequent black language-menu state are recorded separately below. Evidence is in [`process2_redmi_bink_r8_resource_cache_20261025.json`](../../evidence/process2_redmi_bink_r8_resource_cache_20261025.json).

An additional offscreen A/B used the exact captured retail Bink draw #2614, translated shaders, constants, and three R8 planes. Three 8-submit steady samples on the Mali-G76 MC4 averaged 11.21 ms without the cache and 10.26 ms with it (8.4% lower); all six readbacks were bitwise identical, with 921,528 nonblack pixels. A thread-CPU sample measured 2.04 ms uncached versus 1.62 ms cached. The GTX 950 host run also matched output and measured 4.09 ms uncached versus 2.13 ms cached, with validation enabled and zero errors. This isolates one captured draw and bypasses guest Bink decoding and surrounding Copy/Convert work.

The signed APK containing this plugin was installed on the Redmi Note 8 Pro. Two screenshots 66.061 seconds apart match `Franchise_Ident.bik` near source frames 15 and 53; the first match has 0.994 correlation and the second 0.593. This gives an exploratory source-rate estimate of 5.8% for that interval, not a stable playback benchmark. The app log records 630 successful Vulkan submissions between 15:50:17 and 15:52:33, then Copy/Convert operations through 15:53:17 without another successful draw submission. At 15:53:18 the game tried to open raw `D:\tracks\_data\...\menu_background.xml` scene paths; a 15:53:59 device capture is fully black. The log provides temporal evidence around the transition but does not prove that those missing raw paths caused the cutscene or menu stall. The game remains open at PID 22527. Frame matches, APK/plugin hashes, log timestamps, and limits are recorded in [`process2_redmi_cutscene_cache_live_20261025.json`](../../evidence/process2_redmi_cutscene_cache_live_20261025.json), with the [spinning Bink frame](../../evidence/process2_redmi_cutscene_cache_live_a_20261025.png) and [SHIFT title frame](../../evidence/process2_redmi_cutscene_cache_live_b_20261025.png).

At 16:10:49 MSK, ADB still reports PID 22527 and the game as the resumed activity. A fresh 2340x1080 screenshot is byte-identical to the all-black 15:53 capture, and the game log's modification time is still 15:53:18.326. The app remains alive but has produced no later logged Vulkan output; this is a stalled guest/render session, not proof that the raw scene-file probes are its cause. The recheck is recorded in `current_device_recheck` in the same JSON evidence file.

## Redmi Bink cached asynchronous submissions (2026-10-25)

For cached captured-texture submissions that do not request readback, the renderer now keeps at most two submitted frames alive behind Vulkan fences. Their command pools and draw resources stay owned by the texture cache until their fence signals. The R8 upload cache has two mapped staging slots per plane and rotates with those frames, preventing CPU writes from racing transfers still in flight. Reusing a slot waits only for work using that slot; reaching the in-flight limit waits for the oldest frame. Readback calls and submissions without a texture cache retain synchronous completion. The renderer remains Vulkan 1.1 and window-system independent.

The native Vulkan CTest suite and Linux P2 plugin suite both pass 4/4; the renderer regression submits four cached asynchronous frames, then checks a synchronous readback against the prior captured test output. Vulkan validation is enabled for the host renderer test and reports zero validation errors. On the Redmi Note 8 Pro Mali-G76 MC4, an offscreen harness replayed the captured retail Bink draw #2614 (translated retail shaders, captured constants, fullscreen rectangle and three retail R8 planes) using the former synchronous path and this bounded in-flight path. Three samples of eight calls averaged 11.404 ms and 7.748 ms per CPU-side renderer call respectively (32.1% lower for the candidate). All baseline/candidate output bytes match (SHA-256 `8295d56ab66664365991ad06a6fb1f018dc3db37ba07afccdad91b2555f41ca1`). This timing is one isolated draw's submission-call time with fence backpressure, not GPU-only time, full-game FPS, or cutscene playback rate. A fresh ARM64 debug APK was subsequently built from this source and its v2 signature verified; it has not been installed, and the existing game process was left untouched. The package still uses the v0.10.0 Android provider without optional depth/stencil resolve, so the language-selector labels remain unverified on Mali. APK and plugin package hashes are in [`process2_android_async_inflight_apk_20261025.json`](../../evidence/process2_android_async_inflight_apk_20261025.json).

Linux and Android ARM64 P2 plugin artifacts built from this source are kept outside Git at `/home/pes/work/process2-inflight-linux-plugin/plugin-output/librexgpu-shift-native.so` (SHA-256 `42f338bc48e144e9dbc70dd208f9a169f437b506d1c338832896c1a6b83b7f10`) and `/home/pes/work/process2-android-inflight-plugin/plugin-output/librexgpu-shift-natived.so` (SHA-256 `9e2f455c127a183f03b3f1626adda904ffa0ca1b8569003e5c83f772db92801a`). The full device replay method, shader/plane hashes, three timing samples, output hash, and current app-state limitation are recorded in [`process2_redmi_bink_async_inflight_20261025.json`](../../evidence/process2_redmi_bink_async_inflight_20261025.json).

## Redmi Vulkan depth/stencil resolve capability (2026-10-25)

A direct query on the Redmi Note 8 Pro reports Vulkan 1.1.131 and both `VK_KHR_create_renderpass2` and `VK_KHR_depth_stencil_resolve`. The driver reports `supportedDepthResolveModes=0x1` and `supportedStencilResolveModes=0x1`; bit 0 is `VK_RESOLVE_MODE_SAMPLE_ZERO_BIT`. To verify the renderer path rather than only extension enumeration, the current ARM64 `xbox_live_vulkan_renderer_check` was cross-built with NDK r28c and run from `/data/local/tmp`. It created its own Vulkan device with those two extensions enabled, passed a 4x-to-1x depth/stencil SAMPLE_ZERO preservation check, exercised the new cached asynchronous submissions followed by readback equality, and passed the captured sample-zero Copy/Convert regression on Mali-G76 MC4. Exact output: `synthetic offscreen Vulkan 1.1 AutoIndex point and rectangle-list draw plus 4x-to-1x depth/stencil SAMPLE_ZERO preservation and captured sample-zero Copy/Convert passed on Mali-G76 MC4`.

This proves the device driver and P2 renderer support the operation when enabled on the device created by the standalone test. It does not prove retail menu parity, and it does not mean the app's v0.10.0 provider enables the extensions. The Android validation layer is unavailable, so this device run did not use `VK_LAYER_KHRONOS_validation`; host validation remains the validation-layer evidence. The game process (PID 22527) was left running and its installed APK was not changed. Device extension values, CMake commands, binary/shader hashes, result, and scope limits are in [`process2_redmi_resolve_async_renderer_check_20261025.json`](../../evidence/process2_redmi_resolve_async_renderer_check_20261025.json).

## Resolve-enabled Android plugin build boundary (2026-10-25)

The standard CMake plugin target was rebuilt against the SDK branch containing the optional provider capability (`fb151b9`). It built `rexui-vulkan`, the P2 renderer library, and the plugin translation unit with `SHIFT_REXGLUE_OPTIONAL_DEPTH_STENCIL_RESOLVE_PROVIDER=1`; the final target then failed while building its `rexruntime` dependency because Bionic lacks the `getcontext`, `makecontext`, and `swapcontext` declarations used by `fiber_posix.cpp`, and `memory_posix.cpp` references missing `rex::GetAndroidApiLevel`. P2 did not modify those Process 1/runtime files.

As a separate ABI experiment, I manually linked the already-built resolve-enabled P2/plugin/provider objects against the unchanged `librexruntimed.so` extracted from the current v0.10.0 APK. Link-time undefined-symbol checking succeeded, and the new APK candidate below packages that plugin with the old runtime. It has not been loaded on Android, so this does not establish runtime ABI compatibility. Exact standard-build diagnostics and object hashes are in [`process2_android_resolve_plugin_build_20261025.json`](../../evidence/process2_android_resolve_plugin_build_20261025.json).

## Resolve-provider ABI candidate package (2026-10-25)

An ARM64 APK candidate was assembled from the current app package with only the two Vulkan plugin payloads replaced by the resolve-enabled P2 build; the existing `librexruntimed.so` and the remaining package entries were preserved. Both plugin aliases are byte-identical. APK Signature Scheme v3 verification passes with the existing Android Debug certificate. This candidate was not installed because the Wi-Fi ADB endpoint became unavailable (`192.168.1.32:33153` refused connections); the phone still answered ping, but the current connect port could not be discovered by the available ADB mDNS service. The candidate is therefore untested on-device and must not be treated as a working retail build. APK/plugin/runtime hashes and exact packaging procedure are recorded in [`process2_android_resolve_provider_abi_candidate_20261025.json`](../../evidence/process2_android_resolve_provider_abi_candidate_20261025.json).

## Android resolve-provider symbol binding follow-up (2026-10-25)

The resolve-enabled provider is embedded into the plugin while the app still has an older `VulkanProvider` implementation in `librexruntimed.so`. Android builds with the optional depth/stencil resolve provider now pass `-Bsymbolic` when linking the P2 plugin, so references to provider definitions included in that plugin bind to the plugin's own definitions. The regenerated Android link rule contains `-Xlinker -Bsymbolic`. Comparing the manually linked ARM64 candidates, `readelf -rW` reports 23 dynamic relocations against included Vulkan provider/device symbols without the option and none with it. This checks ELF binding in the DSO; it does not verify C++ ABI compatibility or successful loading by Android.

The latest signed APK candidate is `/home/pes/work/process2-latest-renderer-handover-20261025/app-process2-vulkan-latest-bsymbolic-candidate-20261025.apk` (SHA-256 `5006ed47a1510a2389d48de9a27ef0f7a4b8a7c8f8719249b14f242963662305`). Its two plugin aliases are byte-identical (SHA-256 `f84281d8b48cad561f246fa4bf9e58172960ace16193bcd3dcd44d848b9a2f03`), it verifies with the current Android Debug certificate, and it preserves the old `librexruntimed.so` from the base APK. The APK and standalone plugin were handed to Process 1 for possible integration. At handover time ADB was offline and neither artifact had been loaded; the later live run is recorded below. See [`process2_android_resolve_symbol_binding_handover_20261025.json`](../../evidence/process2_android_resolve_symbol_binding_handover_20261025.json).

## Redmi live run with the resolve-enabled provider (2026-10-25)

The same candidate APK was later installed on the Redmi Note 8 Pro and launched in the normal app process. Its on-device APK hash exactly matches the staged candidate. The process logged `VK_KHR_depth_stencil_resolve`, then recorded 1,285 successful Vulkan presenter submissions and 1,285 matching Copy/Convert operations across 74.2 seconds (12,482 captured draw packets); there were no refresh failures. One initial draw was skipped because its captured raster state was incomplete (`valid_mask=0x17038`). The screenshots show the original Loading image, SHIFT title sequence, and legal disclaimer; the disclaimer's text is readable, but this run did not capture the language selector.

At 17:02:29 the guest tried to open both `D:\tracks\_data\instances\scenes\menu_background.xml` and `D:\tracks\_data\static\scenes\menu_background.xml` and received `0xc000000f`. No later presenter submissions appeared, the app process remained alive, and two later screenshots were byte-identical to the disclaimer frame. This is evidence of a guest/runtime transition stop after Vulkan submission; it does not prove the failed path probes caused it. The renderer log and screenshots are in [`process2_redmi_resolve_provider_live_20261025.json`](../../evidence/process2_redmi_resolve_provider_live_20261025.json), [compressed log](../../evidence/process2_redmi_resolve_provider_live_20261025.log.gz), [Loading](../../evidence/process2_redmi_resolve_provider_live_loading_20261025.png), [title sequence](../../evidence/process2_redmi_resolve_provider_live_title_20261025.png), and [disclaimer](../../evidence/process2_redmi_resolve_provider_live_disclaimer_20261025.png). The app data was retained and the game remains open. Language-selector labels on Mali and later gameplay are still unverified.

## Redmi Note 8 Pro live language selector (2026-10-25)

A later run of the same installed retail APK reached the language selector on the Redmi Note 8 Pro. The unmodified phone screenshot shows the `LANGUAGE SELECT` heading, the `SELECT A` prompt, and all six retail entries: `English`, `Français`, `Italiano`, `Deutsch`, `Español`, and `Nederlands`. The non-selected entries are gray but readable. This is an original live retail frame submitted through the Process 2 Vulkan plugin; it is not a synthetic renderer image. This observation supersedes the earlier Android language-label entries above, which were recorded before this selector was captured on Mali.

The app log identifies the active device as Mali-G76 MC4 with Vulkan 1.1.131 and `VK_KHR_depth_stencil_resolve` enabled. Across this startup log it records 578 indexed-draw submissions and 579 accepted Copy/Convert operations, with no presenter refresh failures. Those are run-wide counts, not a selector-only draw trace. The APK hash is `5006ed47a1510a2389d48de9a27ef0f7a4b8a7c8f8719249b14f242963662305`; the installed plugin hash matches the staged P2 artifact. The APK was not reinstalled and app/game data was not cleared for this capture.

After the selector appeared, the app process was suspended with `SIGSTOP` so the phone would remain on the menu for inspection. The focused activity and rendered surface remain open; resume the app with `adb shell run-as com.hanz0hatt0r.nfsshift kill -s CONT 32662`. The screenshot, package/log hashes, device details, and process state are recorded in [`process2_redmi_language_selector_live_android_20261025.json`](../../evidence/process2_redmi_language_selector_live_android_20261025.json), with the [phone screenshot](../../evidence/process2_redmi_language_selector_live_android_20261025.png) and [compressed startup log](../../evidence/process2_redmi_language_selector_live_android_20261025.log.gz). This confirms the selector and its labels on this device only; it does not establish sustained menu operation, cutscene-to-menu progression, race rendering, or full retail parity.

## Redmi post-selector disclaimer stall recheck (2026-10-25)

The installed APK later resumed from the held selector and rendered the original legal disclaimer. The selector capture shows all six language names; the non-selected rows are gray but readable. The disclaimer frame has thin purple horizontal artifacts above and below the text. Three screenshots over eight seconds were byte-identical. One Android `KEYCODE_BUTTON_A` event did not change the screen.

The guest log stopped changing at 17:27:42.690 MSK. Its last successful Vulkan submission at 17:27:42.335 carried 14 captured draw packets; 0.35 seconds later, the guest probed `D:\tracks\_data\instances\scenes\menu_background.xml` and `D:\tracks\_data\static\scenes\menu_background.xml`, both returning `0xc000000f`. The app process and activity remained alive. This records a stable post-intro screen and nearby failed scene-file probes; it does not prove the probes caused the stall or identify the purple artifacts. Process 2 did not modify runtime or asset handling. See [`the device evidence`](../../evidence/process2_redmi_post_selector_disclaimer_stall_android_20261025.json), [screenshot](../../evidence/process2_redmi_post_selector_disclaimer_stall_android_20261025.png), and [compressed guest log](../../evidence/process2_redmi_post_selector_disclaimer_stall_android_20261025.log.gz).

## Redmi post-selector Vulkan output readback (2026-10-25)

A follow-up run enabled the native plugin's one-shot readback with the Android
`wrap.sh` environment. The APK was installed with `-r` and without streaming;
the wrapper marker and both readback variables were confirmed in the app
process, and app data was retained. Its renderer DSO is byte-identical to the
signed production candidate previously handed to Process 1. A separate live
selector capture from this renderer build shows all six original language
labels; in this run English was already persisted, so frame 1,026 is the later
safety-disclaimer screen.

The 1280x720 `VK_FORMAT_A2B10G10R10_UNORM_PACK32` readback at frame 1,026
contains 17,951 non-black pixels and has FNV-1a `AA8BC55196A29A73`. Decoding
the raw words produces the same disclaimer and purple strips seen in the
2340x1080 device screenshot. Cropping the centered 16:9 viewport and scaling
it to 1280x720 yields 894,091 exact RGB pixel matches out of 921,600; the
remaining difference is consistent with display scaling. This compares the
renderer readback with the phone's view of the same output, not with an
independent retail reference.

The run submitted 1,182 frames / 10,471 captured draw packets and accepted
1,182 Copy/Convert operations without presenter refresh failures. Its final
14-draw submit precedes the same missing `menu_background.xml` probes; no later
submit appeared. The log proximity does not identify the cause of the stop.
At 18:04:37, five Android thread samples show the guest main thread at 101% CPU
on average, SDL at 87.8%, two controller threads at 88.8% and 87.2%, and the
audio worker at 57.7%; `SHIFT Native GP` stayed at 0%. The process remained
alive and the screenshot stayed byte-identical. This is evidence that guest
threads remained active while the renderer worker was idle, not a diagnosis of
why submissions stopped. See the [thread sample](../../evidence/process2_redmi_post_selector_frame1026_threads_20261025.log.gz).
The raw readback, decoded image, screenshot, hashes, and run limits are in
[`process2_redmi_post_selector_frame1026_20261025.json`](../../evidence/process2_redmi_post_selector_frame1026_20261025.json),
[`the raw readback`](../../evidence/process2_redmi_post_selector_frame1026_readback_20261025.bin),
[`the decoded readback`](../../evidence/process2_redmi_post_selector_frame1026_readback_decoded_20261025.png),
[`the screenshot`](../../evidence/process2_redmi_post_selector_frame1026_device_20261025.png),
and [`the compressed log`](../../evidence/process2_redmi_post_selector_frame1026_runtime_20261025.log.gz).

## Retail `EVENT_WRITE_SHD` physical/virtual alias check (2026-10-25)

The latest P1 Linux retail log records `EVENT_WRITE_SHD` opcode `0x58` writes
to physical `0x17AF4000` with endian mode 2: the guest value advances `1 -> 3`
and then `3 -> 5`. This physical destination aliases the retail descriptor's
guest virtual base `0xB7AF4000`. The distinct Vd RPTR writeback is at
`0x17AF403C`; it is not the descriptor `+0` word. The P2 handler decodes the
three-word event, applies Xenos `GpuSwap`, and stores through
`TranslatePhysical`, matching ReXGlue 0.10's event handler.

A live-ring regression now seeds the virtual alias with 1, sends a retail-shaped
event to physical `0x17AF4002`, and verifies the resulting value 3 through both
physical and virtual mappings. A selected-frame diagnostic can also write the
normalized vertex and index payloads to `.vertices.bin` and `.indices.bin` via
`SHIFT_NATIVE_VULKAN_DUMP_GEOMETRY_PREFIX`; its synthetic regression compares
the files byte-for-byte with the decoded fixture. Plugin CTest passes 4/4.

The retail log records decoded event fields, not the original Type-3 header
bytes. `0xC0025800` is the canonical unpredicated header derived from opcode
`0x58` and the three payload dwords, not a raw header capture. In a separate
same-run exact-XEX probe, P1 watched the physical host alias and read the guest
virtual alias on every hit: all 360 values matched from `0x5` through `0x2D7`.
Retail wait snapshots showed the descriptor head advancing through that alias,
while RPTR at `0x17AF403C` advanced separately. This closes the alias-mismatch
hypothesis for that run; it does not establish a frontend transition or explain
the guest completion bit. The P1 evidence is
`/home/pes/work/nfs-shift-xbox360-runtime-p1-20261023/evidence/xbox360_linux_guest_ring_physical_virtual_alias_20261025.json`.
See the [P2 implementation regression evidence](../../evidence/process2_event_write_shd_virtual_alias_20261025.json).

## Linux reproduction of the Redmi disclaimer artifact (2026-10-25)

A separate exact-XEX Linux retail run displays the original safety disclaimer
with the same two purple horizontal strips seen in the Redmi Vulkan readback.
The host screenshots at 32 and 62 seconds are byte-identical; the first shows
the disclaimer by submit 551. This confirms the visible artifact is reproduced
by the project-owned guest-draw/Vulkan path on another host. The process mapped
the earlier P2 plugin `42f338bc…b7f10`; its command manifest claimed the current
handoff hash `512eb265…278fa98`, which did not match the mapped file. Therefore
this run does not test the latest handoff binary. The [captured Linux frame](../../evidence/process2_linux_disclaimer_p1_run021_20261025.png)
and [run evidence](../../evidence/process2_linux_disclaimer_p1_run021_20261025.json)
record both the image and that hash discrepancy.

The current P2 plugin can dump the selected submit's prepared vertices,
indices, and texture payloads with `SHIFT_NATIVE_VULKAN_DUMP_DRAW_FRAME`,
`SHIFT_NATIVE_VULKAN_DUMP_GEOMETRY_PREFIX`, and
`SHIFT_NATIVE_VULKAN_DUMP_TEXTURES_PREFIX`. Pair those with
`SHIFT_NATIVE_VULKAN_READBACK_FRAME` and `SHIFT_NATIVE_VULKAN_READBACK_PATH`
to save the corresponding Vulkan output. Submit 551 is the observed Linux
target; the next run should confirm the disclaimer frame number again before
selecting it. The 14 constituent retail draws have not yet been isolated as
the source of the strips.

## Exact-current-plugin live Bink capture (2026-10-25)

A later exact-XEX run loaded the current P2 plugin hash `512eb265…278fa98`
(source commit `b03c9f87`), and its `/proc` mapping matched the run manifest.
The selected Vulkan readback at presenter frame 551 contains the full-screen
retail EA intro mark. The selected bundle includes the three R8 Bink planes
for draw #5380; the raw frame has 920,723 non-black pixels. This proves one
real Bink frame renders with the exact current plugin on the Linux GTX 950.
It only supersedes the earlier DSO-hash mismatch for this Bink capture; it does
not show whether the purple disclaimer strips remain in this build.

The same run had 640 successful presenter refreshes and eight earlier failed
refreshes of 24-draw mixed-sample frames. Those failures report that the Linux
provider did not enable the required depth/stencil resolve capability; they
precede the successful Bink readback. The X11 captures at 32 and 40 seconds are
both black, after the last logged draw submission at 18:50:27.718;
Copy/Convert accepts continue through 18:50:33.646. The P2 plugin calls
`RefreshGuestOutput()` only for swaps that contain resolved draw packets, so
cessation of guest draws is consistent with the later black window. The run
did not read back its last presenter frame or pair a readback with the black
screenshots, so a separate WSI failure is not established. The next
discriminating capture is a failed 24-draw frame and the final successful
presenter frame (frame 640 in this run), each alongside a same-time X11
screenshot, using the resolve-capable provider. See the [run record](../../evidence/process2_linux_exact_p2_bink_frame551_20261025.json),
[decoded frame](../../evidence/process2_linux_exact_p2_bink_frame551_20261025.png),
and [lossless raw readback](../../evidence/process2_linux_exact_p2_bink_frame551_20261025.bin.gz).

## Resolve-capable Linux handoff build (2026-10-26)

The eight logged 24-draw failures from the prior retail run were caused by its
older ReXGlue provider API, which could not enable and report the optional
`VK_KHR_create_renderpass2` / `VK_KHR_depth_stencil_resolve` pair. The renderer
uses this resolve to preserve the shared D24S8 state when the captured stream
transitions from 4x to 1x and subsequent draws still test or write depth or
stencil. It intentionally rejects the frame if the provider cannot confirm
both depth and stencil `SAMPLE_ZERO` support.

A new Linux x86_64 plugin built from P2 HEAD `35dab256` against SDK commit
`fb151b94b4956d1c74ba5052e8838b0829eb9c99` is available at
`/home/pes/work/process2-current-p2-resolve-linux-plugin-20261026/librexgpu-shift-native.so`
(SHA-256 `1fa623feecb9a7ac6c1cd8d6de61bcabc6a4a01b12dfbeb9b0255fa29945042c`).
The GTX 950/Vulkan 1.4 provider reports the pair enabled and SAMPLE_ZERO
supported. Validation-enabled plugin CTest passed 5/5; native Vulkan CTest
passed 4/4, including actual depth/stencil resolve semantics and fail-closed
checks. This is host build and regression evidence only; a retail recapture is
still needed to confirm the previously rejected frames render with this DSO.
See the [build record](../../evidence/process2_linux_resolve_provider_build_20261026.json).

## Redmi guest ring wait after the disclaimer (2026-10-25)

A fresh read-only snapshot at 18:09:48 shows the phone still on the same
disclaimer screenshot, with no new Vulkan output. Over five samples, the guest
main thread averaged 98.2% CPU, SDL 84.3%, and the two controller threads
87.5% / 85.2%; `SHIFT Native GP` stayed at 0%. The GPU worker's
`/proc/.../wchan` was `futex_wait_queue_me`, consistent with the plugin's
`ring_changed_.wait` predicate for new guest ring packets. The main and
controller threads remained runnable. This narrows the current stall to the
guest ring not advancing while the renderer waits; it does not prove why the
guest stopped producing packets or connect that stop to the earlier file
probes. Details and hashes are in
[`the evidence record`](../../evidence/process2_redmi_guest_ring_wait_android_20261025.json)
and [the compressed thread sample](../../evidence/process2_redmi_guest_ring_wait_threads_20261025.log.gz).

A read-only check of the game's Android data directory confirms that
`PakFiles/Menu_Background.bff` is present and byte-identical to both host
retail copies (751,727 bytes; SHA-256 `38346e13ff13f8e3b1fa47afee12fb67ae2b43ab1256476dc6178add55fe8a63`). The checked Xbox PAK index contains `gui/menu_background/menu_background.sgx`, `.enx`, and `tracks/textures/menu_background/menu_background_01.xtx`, with no member named `menu_background.xml`. The guest's loose XML failures therefore do not mean the BFF is absent; this does not prove that an archive fallback is implemented or that the XML failures caused the ring stall. See [`the device archive evidence`](../../evidence/process2_redmi_menu_background_archive_presence_20261025.json) and the validated [historical index record](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/5b913e2875f095b92a02e13fd393f73148889801/evidence/xbox360_menu_background_pak_index_20261024.json).

## Resolve candidate live on Redmi Note 8 Pro (2026-10-25)

The previously recorded resolve-enabled ARM64 candidate was installed by ADB
incremental install after normal APK replacement reported insufficient
storage; game data remained intact. The exact APK hash and mapped renderer DSO
were verified in the running app. It displayed Loading, the EA intro, and the
legal disclaimer, and produced presenter frame-1026 Vulkan readback. After a
center crop and bilinear scale to the readback resolution, 894,091 of 921,600
RGB pixels match the screen capture exactly. This compares two views of the
same output, not against an independent retail reference.

The loading text and yellow-orange filled bar are visible. The disclaimer still
has thin purple bars. The persisted English choice skipped the language
selector; menus after the disclaimer, race graphics, and sustained cutscene
playback remain unverified. The app was left open on the disclaimer. The
[evidence record](../../evidence/process2_redmi_resolve_candidate_live_startup_20261025.json)
contains APK/plugin hashes, readback details, screenshots, and the complete
verification boundary.

## Bounded graphics pipeline object cache (2026-10-25)

The live renderer now reuses compatible `VkPipeline` objects across repeated
draws. Its 128-entry cache key includes the SPIR-V words, vertex layout,
pipeline-relevant raster state, texture binding slots, and render-pass
compatibility key. LRU eviction skips pipelines referenced by in-flight frames.
Descriptor sets and per-draw buffers remain frame-owned; mixed-sample and
copy-only render paths do not use this object cache.

The renderer regression submits identical draws twice and requires identical
readback, then changes an R8 video plane and confirms the cached result matches
an uncached submission. Native Vulkan CTest passed 4/4 and the ReXGlue
live-ring/readback suite passed 5/5 with `VK_LAYER_KHRONOS_validation`
enabled. An ARM64 Android renderer archive also compiled. The Linux plugin and
ARM64 archive are staged under
`/home/pes/work/process2-renderer-handover-pipeline-cache/`; hashes and build
IDs are in [the pipeline-cache handoff evidence](../../evidence/process2_pipeline_cache_handoff_20261025.json).

This verifies cache reuse and output preservation in synthetic regressions. It
does not measure a retail frame-time gain or establish retail image parity. No
Android APK was rebuilt or installed for this cache change, and the current
phone session was left untouched.

## Disclaimer strip source isolation (2026-10-26)

An exact-XEX Linux replay with the pipeline-cache plugin captured retail submit
907 with per-draw geometry, decoded textures, translated shaders, and Vulkan
readback. Four draws (#5058-#5061) place the thin upper/lower strips and sample
the same 512x8 Xenos format-20 texture at `0x0A24B000`. A current read-only
Redmi Note 8 Pro screenshot shows the same disclaimer and strips. The two
outputs are closely aligned after viewport scaling, but the app's mapped DSO
could not be verified from Android, and neither output is an independent Xenos
reference. The capture isolates which draws and texture produce the strips; it
does not determine whether their pixels are intentional or a decode/blend bug.
See the [draw-level record](../../evidence/process2_disclaimer_draw_isolation_20261026.json)
and [Linux Vulkan readback](../../evidence/process2_linux_disclaimer_frame907_readback_20261026.png).

## Redmi Bink draw replay with the pipeline cache (2026-10-26)

An A/B on Mali-G76 replayed the captured retail Bink draw #2614 with identical
SPIR-V and R8 planes. The P2 pipeline-cache build returned byte-identical
readback and reduced replay-thread CPU time by 36% on average (1.303 ms vs.
2.043 ms per call). Average wall time was 8.123 ms for the candidate and
7.887 ms for the previous bounded-in-flight build, so this isolated run does
not show a wall-time gain. It bypasses guest video decode and does not establish
full-game or sustained cutscene performance. The app remained foreground and
unchanged. See the [full A/B evidence](../../evidence/process2_redmi_bink_pipeline_cache_20261026.json)
and the [captured retail draw preview](../../evidence/process2_redmi_bink_retail_draw_replay_20261025.png).

## Bounded Vulkan sampler-object cache (2026-10-25)

The per-device renderer resource cache now reuses identical `VkSampler` states
across captured draws, with a 64-entry bound. Cache clearing waits for
in-flight frames before destroying cached samplers. The native regression
checks reuse, keeps distinct point/linear filter states separate, compares
cached and uncached readbacks, and clears the cache after asynchronous submits.

On the Redmi Note 8 Pro, an ARM64 Release replay of retail Bink draw #2614
returned a byte-identical 1280x720 readback to the prior pipeline-cache build
(SHA-256 `8295d56a…55f41ca1`). Across three alternating pairs, mean wall time
was 7.950 ms vs. 8.000 ms and replay-thread CPU was 1.427 ms vs. 1.466 ms; the
differences are too small to claim a material speedup. Android has no Vulkan
validation layer. The host native Vulkan and P2 plugin suites each pass 4/4
with `VK_LAYER_KHRONOS_validation`; the ARM64 Release renderer archive builds
and the captured retail replay runs on Mali Vulkan 1.1. The active game stayed
resumed with an unchanged screenshot; no APK install, restart, or input was
sent. This is still one offscreen retail draw, not full cutscene or game
performance. See the [Mali A/B evidence](../../evidence/process2_redmi_bink_sampler_cache_20261025.json)
and [matching readback](../../evidence/process2_redmi_bink_sampler_cache_frame2614_20261025.bin.gz).
