# ReXGlue native SHIFT GPU plugin

`rexgpu-shift-native` implements ReXGlue's `IGraphicsSystem` ABI and consumes
the guest PM4 ring without loading the `rexgpu-xenos` renderer. It creates the
SDK's Vulkan presenter with GPU emulation disabled and receives ring updates
through `InitializeRingBuffer` and `CP_RB_WPTR`.

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

A fresh ARM64 P2 plugin was installed and run on Redmi Note 8 Pro. It renders the retail SHIFT loading screen with the yellow-orange progress bar, then the Android Vulkan provider rejects the 24-draw 4x-to-1x depth/stencil frame because the package's SDK does not expose the optional `with_depth_stencil_resolve` capability. The display turns black before the language selector or EA Intro, so the labels are not yet phone-verified. The phone log and actual loading/black frames are recorded in [`process2_redmi_note8pro_language_menu_android_20261025.json`](../../evidence/process2_redmi_note8pro_language_menu_android_20261025.json). The required provider capability is implemented in SDK commit `fb151b9`; integrating it into the Android runtime and rebuilding the consumer is the next shared step. No Process 1 source files were changed.
