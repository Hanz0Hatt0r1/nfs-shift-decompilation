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
resource forms are rejected. The frame path clears the presenter image and renders the collected draws; it does not reconstruct Xenos
EDRAM contents or read the guest frontbuffer as a finished image. The captured
black texture border has unknown alpha, so transparent-black is still
provisional. Target gamma conversion and the complete retail scene are not
yet verified.

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

The latest Android debug APK
(`ff5c30af24013b315280e161cd383c4cd50874a1e096f0d0383364f004a311c6`) was
installed on the Redmi Note 8 Pro. Log `nfs_shift_026.log` confirms one retail
draw submitted at each of two guest swaps and the 1280x720 Copy/Convert
destination matching the swap address. The first Vulkan presenter readback is
still all black (zero non-black pixels, FNV-1a `B161DE6EEC272325`), and the
device screenshot remains black. No later PM4 draw batch was observed after
startup. Android ADB A/Start events from both the default keyboard source and
explicit gamepad source, plus a default-keyboard Enter event, left the
foreground process, runtime log, screenshot, and PM4 output unchanged. The
phone exposes a vendor `uinput-fpc` device with a JOYSTICK source, but Android
denied shell `sendevent` injection, so no physical/controller button was
delivered. The observations are recorded in the
[`android_xbox_key_input_check_20261024`](../../evidence/process2_xbox_live_guest_ring_20261023.json)
evidence entry. This means visible retail output is not ready or verified; the
successful synthetic Vulkan regression only validates the sample-zero
conversion path. See
[`process2_xbox_live_guest_ring_20261023.json`](../../evidence/process2_xbox_live_guest_ring_20261023.json)
for build and device evidence. The game package and plugin are integrated on
Android, but visible retail output and scene parity are not verified. The
`xenos` loader alias can be removed when the host preserves an explicit
`gpu_plugin=shift-native` setting.

A two-sample Android CPU probe showed `Core 2/1: Main` at 100–121% and
`SDLThread` at 81–110% while `SHIFT Native GP` remained at 0%. The screenshot
and runtime-log hashes were unchanged, with two startup swaps and no later PM4
batch. This is consistent with main/SDL execution spinning while the Vulkan
ring worker has no new commands; it does not identify the exact guest function
or prove the cause. Guest execution and scheduling remain Process 1 ownership.
See [`process2_redmi_note8pro_guest_cpu_probe_20261024.txt`](../../evidence/process2_redmi_note8pro_guest_cpu_probe_20261024.txt).

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
