# ReXGlue native SHIFT GPU plugin

`rexgpu-shift-native` implements ReXGlue's `IGraphicsSystem` ABI and consumes
the guest PM4 ring without loading the `rexgpu-xenos` renderer. It creates the
SDK's Vulkan presenter with GPU emulation disabled and receives ring updates
through `InitializeRingBuffer` and `CP_RB_WPTR`.

Set `SHIFT_NATIVE_VULKAN_TRACE_RING=1` to emit a bounded ring-contract trace:
each accepted `CP_RB_WPTR`, the worker's `[RPTR, WPTR)` snapshot, and its
consumption plus guest RPTR writeback. The trace stops after 32,768 records and
is disabled by default; it does not change packet parsing or pointer updates.
Use it to correlate a retail guest queue snapshot with the plugin's actual
write-pointer notification and worker state.

The 2026-10-26 Linux diagnostic build passed all three live-ring CTests with
`VK_LAYER_KHRONOS_validation` forced through the loader. Those tests use
synthetic geometry and resources. Their output does not expose the plugin's
`REXLOG` trace sink. The first two P1 retail runs loaded the old 8,192-record
DSO and exhausted the cap before the `menu_background.xml` probes. A third run
loaded the trace-only 32,768-record build and confirmed `CP_RB_WPTR=5651` in
the plugin;
the worker snapshot `[5645,5657)` expanded 83 packets and completed its RPTR
writeback, consuming the range containing that pointer. Ring processing
continued for about 0.9 seconds after the later XML misses, then stopped before
the process closed. Its screenshot still shows only a very dark disclaimer;
the trace does not establish a menu transition, cutscene, or gameplay. The
trace-only handover path is preserved separately; the 8,192-record binary is
kept with an `-8192cap` suffix. A newer build combines this trace with provider
depth/stencil resolve below. With the same synthetic readback fixture,
trace-off and trace-on output was byte-identical. Build hash, commands, scope,
and P1 trace details are recorded in
[`process2_ring_trace_smoke_20261026.json`](../../evidence/process2_ring_trace_smoke_20261026.json).

The durable copy of the third retail log is
[`process2_p1_ring_trace_20261026.log.gz`](../../evidence/process2_p1_ring_trace_20261026.log.gz);
the associated disclaimer capture is
[`process2_p1_ring_trace_t54_20261026.png`](../../evidence/process2_p1_ring_trace_t54_20261026.png).

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

For an external ARM64 build, `SHIFT_REXGLUE_PREBUILT_RUNTIME` can point at the
matching runtime DSO already packaged by the Android app. The SDK and Vulkan
provider are still compiled from `SHIFT_REXGLUE_SDK_ROOT`, but the plugin target
links the imported runtime instead of rebuilding `rexruntime`. Disable the
plugin CTests for this mode because those host-side tests require the SDK
runtime target. Use the same SDK revision and runtime DSO that the app will load;
this option does not make an ABI-mismatched runtime safe.

```sh
cmake -S native_vulkan/rexglue_plugin -B build/rexgpu-shift-native-android \
  -DSHIFT_REXGLUE_SDK_ROOT=/path/to/rexglue-sdk \
  -DSHIFT_REXGLUE_PREBUILT_RUNTIME=/path/to/librexruntimed.so \
  -DSHIFT_REXGLUE_PLUGIN_OUTPUT_DIR=/path/to/plugin-output \
  -DSHIFT_REXGLUE_NATIVE_BUILD_TESTS=OFF \
  -DCMAKE_TOOLCHAIN_FILE=/path/to/ndk/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-26 \
  -DCMAKE_BUILD_TYPE=Debug
cmake --build build/rexgpu-shift-native-android --target rexgpu-shift-native
```

This is a plugin-only build path: it leaves the SDK runtime and Process 1 files
unchanged. It does not produce a complete APK or validate runtime loading; keep
the existing packaged runtime and verify the plugin in a separately staged app
before installation.

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

The guest-ring path decodes each `PM4_INTERRUPT` CPU mask and now dispatches
the registered GPU callback through its ReXGlue `XHostThread` at that packet's
position in the stream. This preserves ordering with following packets instead
of waiting until the batch ends. The 2026-10-26 exact-XEX callback-stream
capture is recorded in the Process 1 evidence file
`xbox360_linux_callback_stream_targeted_20261026.json` (SHA-256
`e7955956adfdc19fcdf2d80d8bf166ea995173f8702ee71db742ce9683c7de20`). Its
first 30 complete dwords frame as Type-0 writes to registers `0x0100`, `0..2`,
`0x0578`, then three `WAIT_REG_MEM` packets, `PM4_INTERRUPT` with CPU mask 4,
and a Type-0 `CALLBACK_ACK` write of 4 to `0x045E`. The value `0x823A4758` is
one of the register-1 values in the Type-0 write to registers `0..2`, and is
also the reference operand of the third `WAIT_REG_MEM`; the captured prefix
does not write `CALLBACK_ADDRESS` (`0x057C`) or `CALLBACK_CONTEXT` (`0x057D`).
Accordingly, this evidence does not justify executing `0x823A4758` as a GPU
callback or treating `CALLBACK_ACK` as a function pointer. The capture is from
guest stream construction and does not prove that these exact bytes were
submitted or executed by the retail ring. The targeted
`shift_xbox_guest_ring_check` fixture locks down this framing and packet order.
On 2026-10-26, the updated host guest-ring check passed, the Linux plugin and
its six CTest checks built and passed, and the updated plugin translation unit
compiled for Android API 29 / ARM64. The full Android plugin target did not link:
the SDK build stopped earlier in `fiber_posix.cpp` (`getcontext`/
`makecontext`/`swapcontext`) and `memory_posix.cpp` (`GetAndroidApiLevel`),
before compiling/linking the plugin target. The Android check is therefore a
translation-unit compile only, not an APK build or device run.

Earlier Android API 33 guest-ring smoke passed on Redmi Note 8 Pro (Mali-G76
MC4), and the Linux plugin suite passed 3/3 with the readback regression also
passing under Vulkan validation. Those checks preceded the complete Android
game integration; a fresh host CTest run after that integration passed 4/4.
The current-source Linux rerun described above also consumed captured
interrupts and dispatched callbacks. See the `gpu_interrupt_routing_update`
and `post_scalar_destination_live_rerun` entries in the evidence JSON for the
earlier build and test details.

## Captured WAIT_REG_MEM and retail ring boundary (2026-10-26)

The plugin now handles the captured Type-3 `WAIT_REG_MEM` form used by the
retail stream: memory target, Equal comparison, full mask, Xenos endian mode 2,
and poll interval `0x100`. It reads the guest word atomically, applies the
captured endian conversion, and waits until the observed predicate is met or
the ring worker shuts down. Other forms remain unsupported and are logged.

The guest-ring regression snapshots the captured ring `INDIRECT_BUFFER` at
dword `0x1c` (guest address `0x095D0120`, length `0x1df` dwords), expands it,
and checks the captured three-wait/source-1 interrupt prefix at IB byte offset
`0x4b0`. It also includes the three exact nested spans supplied by P1. The test
fills the rest of the outer 479-dword extent with NOPs; it verifies ring
snapshot, recursion, framing, and packet order, not every word of the retail IB.
The live-ring smoke puts the captured waits and interrupt inside an IB and
verifies the production ring worker reaches the interrupt after the waits.
Its resource inputs are synthetic and no guest callback is installed. Linux
CTest passed 6/6 with `VK_LAYER_KHRONOS_validation` requested; the plugin
translation unit compiled for Android API 29 / ARM64. This is not a full
Android plugin link or APK run.

P1's exact-XEX trace recorded `RPTR=0x1c`, final sampled `WPTR=0x49` (45 pending
dwords), and `expand-ok=true` with 149 flattened packets for the first batch
that contained the outer IB. The three nested physical spans also parse through
the production expansion path. This does not prove that the consumer finished
the batch before the GDB harness stopped the title at the guest wait. At that
stop, the target word for a preceding memory wait (`0x1B964004`, reference 1)
was zero. A zero sample alone does not show that no guest thread will write it;
the updated plugin logs entry into a wait and logs completion separately.
The same-sample production completion trace or a non-stopping wait/watchpoint
run is needed before classifying a retail interrupt loss. Full hashes and
capture bounds are in
[`process2_captured_wait_reg_mem_20261026.json`](../../evidence/process2_captured_wait_reg_mem_20261026.json).

### Pre-wait shader effect audit (2026-10-26)

P1's hash-identified exact-XEX capture places the memory wait for
`0x1B964004 == 1` at outer IB byte `0x49C`. I copied that 1,916-byte IB and its
three preceding nested IBs into the P2 evidence directory. The outer draw and
the 24 nested one-point draws load four shader programs. Translating those
exact program bytes maps vertex exports to `gl_Position`/interpolator 0 and
pixel exports to Vulkan color output `shift_color0`; none emits an image,
storage-buffer, or atomic write. The captured copy-destination registers
`0x2318..0x231B` are all zero, no `LOAD_ALU_CONSTANT` packet appears before the
wait, and the render target is EDRAM color base tile 0. The captured shaders
therefore do not directly write the waited guest-physical word.

The new shader-translation regression uses those retail program bytes and
keeps their export targets explicit. The native CMake build passed and CTest
passed 4/4. This rules out only these shader programs as a direct memory
writer; it does not identify a CPU, prior-ring, cache, or device/DMA producer.
The P1 trace's host watchpoints
also saw no write through the sampled physical/A/C/E aliases for about 22
seconds, but cannot observe device/DMA writes or other aliases. See
[`process2_retail_wait_pre_wait_shader_effect_20261026.json`](../../evidence/process2_retail_wait_pre_wait_shader_effect_20261026.json)
and the preserved outer/nested IB binaries beside it.

### Captured COHER_STATUS_HOST register wait (2026-10-26)

The same retail outer IB contains four register-space waits with
`control=0x03`, `poll_address=0xA31`, reference 0, mask `0x80000000`, and
interval 8. Preceding Type-0 writes set `COHER_STATUS_HOST` and its base/size
registers (`0xA31`, `0xA2F`, `0xA30`). The plugin now tracks that captured
register state, marks the host-coherency status dirty on a status write, drains
in-flight Vulkan frame fences on the presenter thread, and clears the status
only after the drain succeeds and no newer register write raced it. Uploaded
guest data is copied into renderer-owned buffers on each draw, so the fence
drain preserves the original guest wait boundary without exposing mapped guest
memory to Vulkan.

The exact register-wait packet has a decoder regression. The live-ring smoke
places that form before the captured memory waits in three submitted batches;
it verifies status clearing and retained base/size values each time. Native
Vulkan checks passed 4/4, Linux plugin checks passed 5/5 with
`VK_LAYER_KHRONOS_validation`, and the Android ARM64 plugin linked. This does
not demonstrate a new exact-XEX run, satisfy the separate memory wait on
`0x1B964004`, or prove a menu/race transition. Process 1 files were not
modified. See
[`process2_coher_status_host_wait_20261026.json`](../../evidence/process2_coher_status_host_wait_20261026.json).

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

For that comparison, `SHIFT_NATIVE_VULKAN_DUMP_TEXTURE_SOURCE_PREFIX` also
saves the exact guest-memory bytes read for each texture in the selected
submit as `.frameN.slotM.textureK.source.bin`. This file preserves Xenos
tiling and endian layout; it is distinct from the decoded `.rgba8`/`.r8`
payload. Set `SHIFT_NATIVE_VULKAN_DUMP_TEXTURE_SOURCE_GUEST_ADDRESS` to a
decimal or `0x`-prefixed guest address to save the first texture match as
`.guest<address>.first.source.bin`, even when the submit number is not known.
The selected-draw live-ring regression checks both selection forms against
the fixture bytes before texture decoding.

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

### Current ring-trace build with depth/stencil resolve

The third P1 ring-trace run used the 32,768-record DSO without the provider
resolve capability. Its log shows eight failed 24-draw presenter refreshes
because 4x-to-1x depth/stencil preservation was not enabled; those failures
occurred before its observed `CP_RB_WPTR=5651`. The current P2 source was
rebuilt against the same resolve-capability SDK branch. The resulting plugin
is at
`/home/pes/work/process2-p1-ring-trace-resolve-handover-20261026/librexgpu-shift-native.so`
(SHA-256 `dec875819cc6146c820838ac8ee52b45b90b83c7bb70d4d521ecc9dcdb4c6ee1`)
and retains the ring trace cap of 32,768. It links against the matching
`librexruntime.so` from that SDK worktree. The provider probe confirms the
resolve pair and SAMPLE_ZERO on the GTX 950; all five plugin tests pass with
`VK_LAYER_KHRONOS_validation`, and `ldd -r` reports no unresolved symbols.

This candidate has not yet had a retail recapture, so it does not establish
that those frames now render or that the menu/cutscene transition succeeds. It
is a Linux x86_64 build; the evidence does not claim Android/ARM64 parity. The
plugin/runtime hashes, build flags, probe and test results, and prior retail
failure timestamps are in the [resolve-provider evidence](../../evidence/process2_linux_resolve_provider_build_20261026.json)
and [retail ring trace record](../../evidence/process2_ring_trace_smoke_20261026.json).

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
At the time of that capture, the expected border shape/color was not available
as an independent reference, so no captured texture or blend state had been
changed based on the screenshot alone.
See the [draw-level record](../../evidence/process2_disclaimer_draw_isolation_20261026.json)
and [Linux Vulkan readback](../../evidence/process2_linux_disclaimer_frame907_readback_20261026.png).

### Gamma target correction for the disclaimer frame (2026-10-26)

Follow-up review found that a captured `RGBA8_GAMMA` frame could gamma-encode
each translated draw and then encode it again in the retail Copy/Convert pass.
When the frame uses the linear `R16G16B16A16_UNORM` intermediate, the renderer
now selects the linear-target fragment shader for gamma draws and applies the
captured Xenos gamma conversion once at Copy/Convert. Both regular 4x-MSAA and
the captured 4x-to-1x resolve path are covered.

The regression uses synthetic shaders to require linear 0.25 in the
intermediate and approximately 0.498 in the final Xenos 10-bit output. Core
renderer checks passed 4/4 and plugin checks passed 5/5 with Vulkan validation
enabled; the Android ARM64 plugin also compiled. The rebuilt binaries were
passed to Process 1 for a follow-up retail capture. The existing disclaimer
screenshots predate these binaries, so the reported frame appearance is not
yet visually confirmed. This regression rules out double gamma encoding in
the tested paths; it does not establish full disclaimer-frame parity or
confirm that every visible strip pixel is wrong. Build hashes and test scope
are recorded in
[`process2_disclaimer_gamma_target_fix_20261026.json`](../../evidence/process2_disclaimer_gamma_target_fix_20261026.json).
The updated ARM64 offscreen renderer regression was then run directly on the
Redmi Note 8 Pro and passed on Mali-G76 MC4, including the synthetic gamma
target and 4x-to-1x Copy/Convert cases. This verifies the intermediate format
and shader path on the phone GPU; it does not run the game or confirm the
retail border image.
The Redmi install attempt was blocked by insufficient internal storage; the
package is temporarily unregistered after `uninstall -k`, which retained its
data/cache. The updated signed APK and the previous signed APK backup are in
the handoff directory recorded by that evidence. A device screenshot with the
corrected plugin remains pending.

### Packed-mip offset correction for the disclaimer border (2026-10-26)

The captured 512x8 DXT4/5 texture used by retail draws #5058-#5061 has the
packed-mip flag set, with the mip tail beginning at level 0. Its base image
therefore begins four DXT block rows into the tiled allocation. The previous
decode started at block row 0, which produced broken purple/gray fragments in
the thin upper and lower border. The tiled DXT and RGBA8 paths now apply the
captured level-0 packed offset; unsupported packed-linear layouts still fail
closed.

The exact four captured retail draws were replayed offscreen on the Redmi Note
8 Pro / Mali-G76. Their border rows are now continuous across the captured
920-pixel span. The Linux native checks and captured-draw replay passed with
Vulkan validation, and the same capture fixture passed in the Android ARM64
renderer check. This establishes the texture-address correction for those
draws; no independent original-console image was available to establish exact
border color or thickness. See
[`process2_disclaimer_packed_mip0_fix_20261026.json`](../../evidence/process2_disclaimer_packed_mip0_fix_20261026.json)
and the [Mali replay](../../evidence/process2_disclaimer_packed_mip0_replay_mali_20261026.png).

After commit `ccdee6b4`, the current ARM64 renderer-check executable was rebuilt
and run directly on the Redmi Note 8 Pro with the same raw guest texture,
expected decoded bytes, four captured retail vertex buffers, shaders, and
Copy/Convert state. The run passed on Mali-G76 MC4. Its raw 1280x720
A2B10G10R10 readback contains exactly 7,360 nonblack pixels: eight continuous
four-pixel-high rows across x=180..1099. This is a replay of the four border
draws only, not the full disclaimer frame or a live game session. No game APK
was installed or launched. The device has no
`VK_LAYER_KHRONOS_validation`; host validation remains the layer coverage.
See [`the current ARM64 replay evidence`](../../evidence/process2_disclaimer_current_arm64_mali_20261026.json),
[decoded strip replay](../../evidence/process2_disclaimer_current_arm64_mali_replay_20261026.png),
and [compressed raw readback](../../evidence/process2_disclaimer_current_arm64_mali_readback_20261026.bin.gz).

### Guest coherency wait owner tracing (2026-10-26)

The exact retail run remains blocked at `WAIT_REG_MEM` guest physical address
`0x1B964004` (reference `1`, mask `0xFFFFFFFF`, endian mode `2`). The captured
outer IB has no memory-write packet before that wait. Its later
`EVENT_WRITE_SHD` packets write `0x17AF4004` and `0x17AF4000`, so they do not
explain the wait. The raw bytes of the preceding ring-root IBs were not retained,
and the producer of `0x1B964004` is still unknown.

The ring trace optionally logs raw dwords for the first 16 candidate guest
memory-write packets per opcode, with their source IB and byte offset. Include
`SHIFT_NATIVE_VULKAN_TRACE_RING=1` in a retail capture. The initial candidate
set omitted `EVENT_WRITE_SHD` (`0x58`), although that opcode is handled as a
guest-memory write elsewhere in the plugin; the candidate set and live-ring
regression now include it. This is logging only: it does not write guest
memory or change wait behavior. Host CTest verifies the trace against a
synthetic `EVENT_WRITE_SHD` packet. Android launchers that do not run the
packaged wrapper can use `-DSHIFT_NATIVE_VULKAN_TRACE_RING_DEFAULT_ON=ON` for a
diagnostic build; production builds leave this option off. The corrected
Redmi capture still finds no observed writer for `0x1B964004` in the scanned
batches and does not identify the CPU-side producer. See the
[`wait-owner trace build record`](../../evidence/process2_guest_wait_owner_trace_build_20261026.json).

### Raw nested indirect-buffer snapshot (2026-10-26)

The trace now retains the raw big-endian dwords of up to eight unique nested
guest indirect buffers per ring-worker session, capped at 4 KiB per buffer.
This is a read-only diagnostic and does not alter packet dispatch or wait
behavior. A live Redmi run captured seven buffers; the `WAIT_REG_MEM` packet
is at byte offset 1180 in `0x095D0120` and polls `0x1B964004` for value 1. The
preceding outer buffer `0x095D0000` contains two observed `EVENT_WRITE_SHD`
targets, `0x17AF4004` and `0x17AF4000`; neither matches the wait address. The
complete PM4 framing of all seven saved buffers finds no explicit PM4 memory
write to the wait address before that packet. The wait buffer itself contains
an `EVENT_WRITE` marker at offset 1792 and two more `EVENT_WRITE_SHD` packets
at offsets 1884 and 1900, all after the wait; the worker cannot reach them
until the wait completes. This does not rule out a CPU producer, shader/export
writes, or writes outside the captured buffers. The app remained top-resumed
but black at the wait. The saved big-endian buffers and log are linked from the
[`Redmi indirect-buffer trace record`](../../evidence/process2_redmi_ring_indirect_buffers_20261026.json).

The separate disclaimer border replay confirms only the four captured retail
strip draws: the packed-mip correction produces continuous gray top and
bottom rules. The latest full live frame cannot be recaptured until the
startup wait is resolved, and exact color or thickness remains unverified
against an independent original-console image.

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

## Nested retail completion packet audit (2026-10-25)

P1 supplied a retail queue snapshot with `head=4519`, `tail=4529`, predicate
`0x04` (mask `0x02` clear), and a 28-dword indirect buffer at `0x09692CE0`.
The P2 root stream expands `PM4_INDIRECT_BUFFER` packets recursively and the
same dispatcher processes nested packets; opcode `0x58` is handled by
`decode_guest_event_write_shd` and the `EVENT_WRITE_SHD` branch. The exact IB
contains two such packets. The first decodes `0x17AF4006` as physical
`0x17AF4004`, endian mode 2, value `0xA9692D24`; the second decodes
`0x17AF4002` as physical `0x17AF4000`, endian mode 2, value `0x1089`.

That second immediate value is 4233, while P1's hypothesized `tail-2` cursor is
4527 (`0x11AF`). This IB therefore does not publish the hypothesized completion
cursor. P2 must store the packet's literal value after Xenos `GpuSwap`; it must
not substitute the queue tail or set predicate bit `0x02`. `EVENT_WRITE_SHD`
is a guest-memory write and is distinct from the `PM4_INTERRUPT` callback path.
The address/endian/value semantics match ReXGlue's
`CommandProcessor::ExecutePacketType3_EVENT_WRITE_SHD` and the earlier
[physical/virtual alias regression](../../evidence/process2_event_write_shd_virtual_alias_20261025.json).

A focused `shift_xbox_guest_ring_check` fixture now feeds this exact IB through
the indirect-buffer expander and asserts both nested event destinations,
endianness, and immediate values. The test passes. It verifies framing and
decoding; it does not prove that this packet was the final queue completion in
P1's wait sample or that a later indirect buffer did not contain another event.
The current evidence points to an event value older than the waiter expects,
not a renderer-side packet decode failure. The full capture and limits are in
[`process2_retail_nested_completion_event_20261025.json`](../../evidence/process2_retail_nested_completion_event_20261025.json).

In a corroborating retail run with the same mapped plugin and runtime hashes,
the renderer snapshotted `[4517,4529)`, expanded 362 packets, then completed
that range 30 ms later and wrote its separate Vd RPTR at `0x17AF403C` from
`0x11A5` to `0x11B1`; four captured draws were submitted in that batch. This
confirms renderer ring progress around the observed cursor values. The log does
not include indirect-buffer guest addresses, so it does not prove that this
batch contained the supplied `0x09692CE0` IB. The exact nested-IB regression
passes, and all five P2 plugin CTests pass.
The corroborating run metadata and compressed full log are preserved in
[`process2_nested_completion_retail_run_20261025.json`](../../evidence/process2_nested_completion_retail_run_20261025.json)
and [`the compressed log`](../../evidence/process2_nested_completion_retail_run_20261025.log.gz).

## Current Android language selector and title sequence (2026-10-26)

The current signed candidate APK (`e9185d08…9136c10c9`) was installed on the
Redmi Note 8 Pro with incremental ADB install, preserving app data and retail
assets. Its P2 ARM64 plugin aliases are identical (SHA-256
`53eda9ca…6da5e13b`); the packaged runtime DSO is the unchanged
`724978a1…6c888a`. In the live selector screenshot, `LANGUAGE SELECT`, `SELECT
A`, and all six entries—`English`, `Français`, `Italiano`, `Deutsch`,
`Español`, and `Nederlands`—are visible. The highlighted English row is
orange, and the unselected rows remain readable in gray. This directly
confirms the reported missing-label symptom is fixed in this candidate on the
Mali device; the screenshot is retail output, not a synthetic render.

After one Android A-button event, the app rendered the original NFS SHIFT
title sequence and then reached the legal disclaimer. The saved guest log
contains 1,233 presenter submission events carrying 11,267 indexed draw
packets and 1,233 accepted captured Copy/Convert operations, with no presenter
refresh failures. Draw #0 remains fail-closed because its captured raster
register state is incomplete (`valid_mask=0x17038`). The last submissions are
followed by failed `menu_background.xml` opens with status `0xc000000f`; timing
does not establish that these misses caused the subsequent disclaimer stall.
The complete package, screenshot, and log hashes are in
[`the device evidence`](../../evidence/process2_redmi_language_selector_latest_android_20261026.json),
[the language selector](../../evidence/process2_redmi_language_selector_latest_android_20261026.png),
[the title sequence](../../evidence/process2_redmi_language_selector_title_latest_android_20261026.png),
and [the compressed guest log](../../evidence/process2_redmi_language_selector_latest_android_20261026.log.gz).

The full Android application target still cannot be rebuilt with the current
SDK because its existing POSIX fiber source calls Bionic-unavailable
`getcontext`, `makecontext`, and `swapcontext`. This candidate instead packages
the manually linked current P2 plugin against the unchanged runtime DSO; its
successful live launch verifies that package combination, but not a full
runtime rebuild. The plugin-only build path below now links the P2 plugin to an
existing runtime DSO directly, without trying to build the SDK runtime target.
A later read-only ADB recheck confirmed PID 17268 remained
top-resumed on the legal disclaimer; Process 2 sent no more input and did not
close the app. The [current screen](../../evidence/process2_redmi_language_selector_latest_current_screen_20261026.png)
is preserved. The phone does not provide `VK_LAYER_KHRONOS_validation`; device
validation-layer coverage remains absent. The post-disclaimer menu, race, and
complete retail parity are still unverified.

## Initial P1-compatible Linux renderer handoff (2026-10-26)

The current P2 source was rebuilt as an x86_64 ReXGlue plugin against SDK
commit `fb151b94b4956d1c74ba5052e8838b0829eb9c99`, which matches the runtime
used for Process 1's resolve-capable retail work. The plugin is
`/home/pes/work/process2-latest-renderer-handover-20261026/linux-amd64/librexgpu-shift-native.so`
(SHA-256 `dec875819cc6146c820838ac8ee52b45b90b83c7bb70d4d521ecc9dcdb4c6ee1`,
Build ID `60e3a7549235b97386d145ada68592df8de1590e`). It is paired with the
same directory's `librexruntime.so` (SHA-256
`127181adbfb99b65e9d1a8f1d6aed12308e1cf320b86067588ad421f17eda68e`). `ldd
-r` reports no unresolved symbols.

All five plugin CTests pass with `VK_LAYER_KHRONOS_validation` forced through
the loader, and all four native Vulkan CTests pass with the layer forced. The
shader translator regression checks that a nonzero Xenos interpolator remains
at Vulkan location 1 and the pixel shader reads `r[1]`; this covers the
language-label failure mechanism. These host tests exercise synthetic ring,
shader, and resource fixtures. Process 1 still needs a fresh retail Linux run
with this exact plugin/runtime pair before the build can be called validated
against its current retail session. Plugin/runtime hashes and test logs are
recorded in
[`the renderer handoff evidence`](../../evidence/process2_latest_renderer_handoff_20261026.json).
The compressed [plugin CTest log](../../evidence/process2_latest_renderer_plugin_ctest_20261026.log.gz)
and [native Vulkan CTest log](../../evidence/process2_latest_native_vulkan_ctest_20261026.log.gz)
are preserved alongside it.

## Android ARM64 plugin build with the existing runtime (2026-10-26)

The latest P2 renderer core was linked into a new ARM64 `rexgpu-shift-native`
plugin using `SHIFT_REXGLUE_PREBUILT_RUNTIME`. The build used the resolve-capable
SDK at commit `fb151b94b4956d1c74ba5052e8838b0829eb9c99`, Android NDK 28.2, and
the exact `librexruntimed.so` already present in the previous app candidate.
`rexui-vulkan`, the current P2 renderer, and the plugin all built successfully;
the SDK runtime target was not built. The resulting DSO depends on
`librexruntimed.so`, has the Android ARM64 ABI, and retains the provider's
`-Bsymbolic` binding.

A signed APK candidate was assembled from the prior Android APK by replacing
only `librexgpu-shift-natived.so` and its `librexgpu-xenosd.so` loader alias.
The two new aliases are byte-identical, all other APK entries retain their
content, the packaged runtime hash is unchanged, the package verifies with the
existing Android Debug certificate, and uncompressed native libraries are
16-KiB aligned. The candidate is available at
`/home/pes/work/process2-latest-renderer-handover-20261026/android-plugin-buffer-cache-20261026/app-process2-vulkan-buffer-cache-20261026.apk`.
It has not been installed: the Redmi app remains open on its disclaimer. The
updated plugin has therefore not yet been loaded by the game, and this package
does not establish new retail output or parity. Exact hashes and the read-only
device state are recorded in
[`process2_android_prebuilt_runtime_plugin_20261026.json`](../../evidence/process2_android_prebuilt_runtime_plugin_20261026.json).

## Fence-safe per-draw upload buffer reuse (2026-10-26)

The renderer now reuses vertex, index, vertex-uniform, and pixel-uniform upload
buffers across two fenced in-flight slots per captured draw. Host-visible
buffers stay mapped; noncoherent writes are flushed before submission. Reuse
follows the existing frame-fence retirement path, while uncached and copy-draw
requests keep the prior allocation behavior. The cache is bounded to 16 MiB,
128 draw entries, and 120 submitted frames of inactivity. It does not alter
draw state, shader translation, or pixels by design.

The regression checks that the second in-flight slot stabilizes buffer count,
later output remains byte-identical, and clearing the cache releases all
entries. Host CTest passes 4/4; the renderer test explicitly reports Vulkan
validation enabled on GTX 950. The ARM64 offscreen renderer check also passes on
the Redmi Note 8 Pro Mali-G76 MC4 with Vulkan 1.1.131. Android does not provide
the Khronos validation layer. These are synthetic/resource-lifetime checks;
they do not measure end-to-end frame time or prove a performance gain. The
latest plugin-only APK contains this core but has not been installed; the game
remains open on the legal disclaimer. See
[`process2_draw_upload_buffer_cache_20261026.json`](../../evidence/process2_draw_upload_buffer_cache_20261026.json)
and its [host validation log](../../evidence/process2_draw_upload_buffer_cache_renderer_test_20261026.log).

## Captured 4:1 sampler anisotropy follow-up (2026-10-26)

The retail D3D9 sampler audit captured texture `0x0679a000`, format 19, with
anisotropy enum 3 (4:1). The renderer now requests Vulkan `samplerAnisotropy`
independently of Xenos GPU-emulation features, and caps the sampler at the
captured ratio and the device limit. The SDK change ([PR #6](https://github.com/Hanz0Hatt0r1/rexglue-sdk/pull/6)) adds overloads while
preserving the existing provider/device signatures; the legacy overload still
enables anisotropy when GPU emulation is requested. Linux CTest passes with
`VK_LAYER_KHRONOS_validation`; the dedicated offscreen renderer regression
also passes on the Redmi Note 8 Pro Mali-G76 MC4 and reports the 4:1 sampler
path. Android does not provide the Khronos validation layer.

The Linux handoff pair is in
`/home/pes/work/process2-latest-renderer-handover-20261026/linux-anisotropy-20261026/`.
The signed Android candidate APK is in
`/home/pes/work/process2-latest-renderer-handover-20261026/android-plugin-sampler-anisotropy-20261026/`;
it preserves the previous APK's signature and changes only the two P2 plugin
aliases. That candidate has not been installed or loaded by the game. The
Android provider-level capability harness could not run because the reused
runtime crashes during `dlopen` before the test hook; the independent
renderer-core check passed on-device. These synthetic tests do not prove new
retail output, selector/cutscene rendering, or full scene parity. Details,
hashes, and limitations are in
[`process2_sampler_anisotropy_capability_20261026.json`](../../evidence/process2_sampler_anisotropy_capability_20261026.json).

## Bounded captured-shader translation cache (2026-10-26)

`PrepareCapturedDrawResources` translates the same guest VS and PS again for
each retail draw; textured PS translation runs a second time after captured
fetch descriptors provide the real swizzle/sign options. The existing Vulkan
pipeline cache starts after translation, so it does not avoid Xenos instruction
decode and GLSL generation. A renderer-owned FIFO cache now keys the stage,
exact shader bytes, boolean constants, gamma target, clip/window transform
(including float bit patterns), and all 32 captured texture swizzles and sign
modes. It stores successful results only, is bounded to 128 entries and 4 MiB
of estimated payload, and clears after the ring worker stops. Debug batch logs
expose cumulative cache hits/misses and retained payload for a retail run.

The regression compares the complete cached result with direct translation of
the retail pixel-shader slice used by the b128/b129 capture audit. It checks
cache hits, b128/b129 selection, texture swizzle/sign, gamma target, failed
translation retry, FIFO capacity eviction, and clear. Native Vulkan CTest
passes 4/4 and Linux plugin CTest passes 5/5 with
`VK_LAYER_KHRONOS_validation` forced. The ARM64 plugin also builds with NDK
28.2/API 26 against the existing runtime. Its SHA-256 is
`968c7c8a…538c27f`, Build ID `8c4d336e0e4d4ee1028fa7ba9738b7d30563ff4d`.
The refreshed x86_64 plugin for Process 1 is
`/home/pes/work/process2-p1-ring-trace-resolve-handover-20261026/librexgpu-shift-native.so`
(SHA-256 `f1d6394bfa01dd65b2472d50eda64b1dd5ceade8993a43771b0e73b84090f95c`,
Build ID `e76c6515f0d0737753023971fcc68916d0aaf706`), paired with SDK runtime
`/home/pes/work/rexglue-sdk-process2-resolve-20261024/out/linux-amd64/librexruntime.so`
(SHA-256 `d8faeb3973a1a2564dea021f19d0418fa718268dadebd414b0006a94a9062253`).
`ldd -r` resolves it without undefined symbols. This pair was rebuilt from
Process 2 commit `8e76681ccc6f29462ba43329c6ef45f46dcedadf` and is the latest
Linux handoff for the live retail run.

The shader-cache plugin was installed and loaded by the live game on the Redmi
Note 8 Pro. Its loading/title and legal disclaimer were observed, but the log
does not include cache hit/miss counters, so device hit rate and frame-time
change remain unmeasured. The Android session remains open on the legal
disclaimer. Menu-after-disclaimer, race output, and full retail parity are
still unverified. Artifact identities and verification limits are in
[`process2_shader_translation_cache_20261026.json`](../../evidence/process2_shader_translation_cache_20261026.json).

## Selected pre-Copy color-target readback (2026-10-26)

`SHIFT_NATIVE_VULKAN_SOURCE_READBACK_PATH` opts one submitted frame into a
readback of the captured render target after its draw pass and immediately
before Copy/Convert. It also reads back the final presenter image, so the log
records source and output extents, Vulkan formats, non-black pixel counts, and
FNV-1a64 hashes separately. `SHIFT_NATIVE_VULKAN_READBACK_FRAME` selects the
same frame for both images; when omitted, setting the source path selects frame
1. The source file contains tightly packed raw format bytes.

For the homogeneous 4x path, Vulkan cannot copy a multisampled image directly
to a host buffer. The diagnostic resolves a sidecar image using the Vulkan
average resolve mode, reads that image, and restores the original 4x target to
the same shader-read layout used by Copy/Convert. The report labels this as a
4-sample average resolve; it is a diagnostic of the multisample target, not a
byte-for-byte capture of the sample-zero value consumed by the existing
Copy/Convert shader. For the mixed 4x-to-1x path, it reads the final 1x source
after the existing render-pass resolve and 1x draws. If optional staging or
transfer-image setup is unsupported, the final image remains submitted and the
source status is logged as unsupported with its reason. Frames without a
captured Copy/Convert source also report unsupported.

The renderer CTest's synthetic regression produces a colored 4x source with a
black Copy shader, then a black source with the same black Copy shader. It
checks the source and final images independently and passed on the NVIDIA GTX
950 with `VK_LAYER_KHRONOS_validation` enabled. The Linux plugin DSO compiled
and its factory and Vulkan-resolve capability tests passed. The updated ARM64
renderer check also passed offscreen on the Redmi Note 8 Pro Mali-G76 MC4 with
Vulkan 1.1; Android has no Khronos validation layer. The retail app stayed open
on its disclaimer, and the updated plugin was not installed. The remaining live
ring plugin CTests were not rerun because enabling them caused their external
ReXGlue SDK build to fail on unrelated `getcontext`/SSSE3 configuration errors.
This readback has not yet been exercised against a retail frame; it is a
diagnostic, not evidence of retail visual parity. See
[`process2_source_color_readback_20261026.json`](../../evidence/process2_source_color_readback_20261026.json)
for build identities, test results, and limits.

For an exact selected presenter frame, `SHIFT_NATIVE_VULKAN_DUMP_DRAW_FRAME`
also enables one Vulkan 1.1 non-precise occlusion query per prepared draw. The
log maps each submitted Vulkan draw back to its decoded guest draw-packet index
and reports whether any samples passed. A positive result confirms raster and
depth/stencil coverage, but does not prove that the shader or color-write mask
changed RGB; zero helps isolate geometry, clipping, and depth/stencil issues.
Query setup is optional and a failed or unavailable query leaves rendering
unchanged. The renderer regression checks both a colored draw and a black
source whose test draw still passes occlusion. Host validation and the
offscreen Redmi Note 8 Pro Mali-G76 MC4 Vulkan 1.1 run passed. This query path
has not yet been collected from a retail frame; it does not revise the black
frame-400 evidence above.

The updated plugin also compiles and links as an Android ARM64 debug DSO with
NDK r28c/API 29. It links against the matching runtime built from the existing
Android SDK snapshot; no APK was rebuilt or installed, and this DSO was not
loaded into the running game. A separate Android factory smoke loaded the DSO
and checked the GPU ABI/backend on the Redmi Note 8 Pro; it submitted no draws.
The retail app remained resumed and the temporary test files were removed. The
Android build emitted one SDK FPCR inline assembly width warning. Artifact
hashes and build IDs are recorded in the source-readback evidence JSON.

Process 1 tried the selected frame again with this plugin and the matching
runtime in an isolated Linux retail run. The host stopped with `SIGBUS` after
about 194 seconds; its log ended at `waiting for guest PM4`, with no draw-query
events and no source or presenter readback files. This run therefore says
nothing new about renderer output or the cause of the earlier black source.
The Redmi app remained open on the legal disclaimer; its read-only screenshot
hash is unchanged. Details are in the `latest_plugin_retail_visibility_attempt`
record in the source-readback evidence JSON.

## Bounded CPU-side R8 video-plane scratch cache (2026-10-26)

The live Bink path receives captured linear R8 planes and converts each plane
to the renderer's upload input. The plugin now reuses the CPU vectors for
recurring planes, keyed by guest draw slot, fetch constant, and dimensions.
The cache has a 16 MiB cap, rejects duplicate simultaneous leases, and falls
back to ordinary allocation when a plane does not fit. The upload path copies
the bytes into Vulkan-owned staging before returning, so the ring worker
recycles the CPU vector only after that synchronous preparation finishes.
GPU image/upload caching and the bytes converted or copied per frame are
unchanged.

The regression verifies the reuse, fresh-frame overwrite, immutable released
payload, duplicate-lease rejection, and budget bypass. It passed on x86_64 and
as an ARM64 executable on the Redmi Note 8 Pro. The Linux plugin and its six
CTest cases passed with `VK_LAYER_KHRONOS_validation` forced; the native Vulkan
renderer CTest suite also passed 4/4 with the layer. `ldd -r` found no unresolved
symbols in the built plugin. This measures allocation reuse only: the plugin
was not installed for a new live retail run, and video playback speed,
allocation counts under the guest workload, frame time, and retail parity were
not measured. The menu-selector language labels were separately verified on
the current Redmi candidate and all six are readable, including the gray
unselected rows. Build identities and the exact test record are in
[`process2_r8_upload_scratch_20261026.json`](../../evidence/process2_r8_upload_scratch_20261026.json).

## Bounded Vulkan descriptor-layout cache (2026-10-26)

Captured draws now reuse Vulkan descriptor-set layouts and pipeline layouts
when their texture binding numbers match. The cache is bounded to 128
compatible layouts and is cleared with the existing per-device renderer cache
after in-flight work completes. Descriptor pools and descriptor sets remain
per draw because their buffer and image bindings change. The renderer
regression verifies that repeated submissions reuse layouts without changing
the offscreen pixels, and that clearing releases the retained layouts.

The native Vulkan renderer tests passed 4/4 and the Linux plugin tests passed
6/6 with `VK_LAYER_KHRONOS_validation` enabled. The updated offscreen renderer
check also passed as ARM64 on the Redmi Note 8 Pro Mali-G76 MC4 using Vulkan
1.1. The Linux plugin links cleanly against the matching ReXGlue runtime. No
fresh retail playback with this layout cache was performed; no retail parity
or frame-time improvement is claimed. Exact build identities and evidence are
in [`process2_descriptor_layout_cache_20261026.json`](../../evidence/process2_descriptor_layout_cache_20261026.json).

## Redmi live candidate with the layout cache (2026-10-26)

The latest ARM64 plugin was linked against the exact runtime already present
in the installed APK (`724978a1…c888a`) and packaged by replacing only the two
renderer aliases. The signed APK passed v3 signature verification and 16-KiB
native-library alignment. It was installed with `adb install -r`; game data
was preserved. After launch, the retail loading screen showed the expected
orange filled bar, dark empty bar, and complete “Loading...” label. The
language selector showed all six retail labels, then the original disclaimer
appeared with its known purple edge strips.

The phone later reported the launcher as top-resumed and no game process. No
Process 2 stop or data clear was issued, and no app-specific fatal signal was
captured; the process exit cause remains unknown. This run did not reach a
post-disclaimer menu, Bink frame, or race scene. It confirms current-build
startup screen rendering only and makes no cutscene throughput or full parity
claim. See
[`process2_android_descriptor_layout_live_candidate_20261026.json`](../../evidence/process2_android_descriptor_layout_live_candidate_20261026.json)
and its three screenshots for hashes and exact limits.

## Retail wait-value trace on the corrected Android alias (2026-10-26)

The bounded ring trace now samples the first raw guest value, its Xenos-endian
decoded value, and the wait condition, then records changes or one-second
samples (at most eight per wait). It only reads guest memory; the captured wait
and its polling behavior are unchanged. The synthetic ring regression uses
the exact retail `WAIT_REG_MEM` operands from guest `0x095D0120`, byte offset
1180, and verifies the value transition at `0x1B964004` from 0 to 1. Linux
plugin CTest passes 7/7 with this regression.

The first Android package made for this trace contained the new P2 DSO at
`librexgpu-shift-natived.so` but retained an older P2 Vulkan DSO at the host's
`librexgpu-xenosd.so` loader path. The process map showed that stale alias was
loaded; it was still the emulator-free P2 frontend, but it lacked this new
sampling code. The corrected signed candidate replaces both entries with the
same P2 DSO; the installed process maps `librexgpu-xenosd.so`, whose file hash
matches the P2 plugin. Verify both APK entries against the built plugin hash
before installing future candidates.

With the corrected alias loaded on Redmi Note 8 Pro / Mali-G76 MC4, the retail
worker reached `WAIT_REG_MEM` at `0x1B964004` and sampled raw/decoded value 0
through poll 7000 (7.824 seconds), against reference 1, so the condition stayed
false. The app remained black and the ring stopped before submitting a guest
Vulkan frame. The seven-buffer PM4 scan found no explicit write to this address
before the wait, but it does not cover CPU writes, shader/export stores, or
unrelated command streams. This confirms the current P2 plugin is running and
narrows the live blocker to an unsatisfied guest wait; its producer path is
still unknown. It does not claim a visible retail frame. APK, loaded-alias
identity, samples, screenshot, and limits are in
[`process2_redmi_wait_reg_mem_value_trace_20261026.json`](../../evidence/process2_redmi_wait_reg_mem_value_trace_20261026.json).

The later provider-resolve capture still stops at a separate graphics limit:
its transition batch contains an all-four-sample format-26 resolve, seven
single-sample format-31 intermediate copies at different extents, and a final
frontbuffer copy. The current renderer handles the final copy path but does not
write those internal copies to guest memory. Intermediate destinations are
retained as GPU-resident Vulkan images keyed by the captured destination
layout, while compatible draw and copy segments execute in PM4 order. The
renderer also retains same-layout EDRAM targets and can feed a later format-31
linear base-level texture fetch from an exact matching cached copy image. This
does not reinterpret aliased target layouts. The captured draw-12 texture is a
tiled base-level format-31 view at `0x0CD64000`, separate from the preceding
copy at `0x0CD63000`; its captured descriptor words are
`80424956 CD6409F 00000000 01281691 00000003 00000210` (`mip_min=0`,
`mip_max=0`). The exact-copy cache path correctly does not alias these
addresses. The renderer now accepts this tiled 32bpp guest-memory layout and
uploads it as `R16G16_SFLOAT`. The draw-input regression verifies descriptor
decode and a synthetic tile/endian payload; the retail texel bytes and rendered
sample were not captured or compared, so this does not establish draw-12 parity.
The 14-draw package remains incomplete.
See the exact phone register sequence and earlier failure limits in
[`process2_redmi_transition_copy_chain_20261026.json`](../../evidence/process2_redmi_transition_copy_chain_20261026.json).

## Captured 16-bit floating-point targets (2026-10-26)

The transition capture also contains a single-sample Xenos color format 6
(`16_16_FLOAT`) target at pitch 320 and a 243x243 viewport/scissor. The raster
decoder maps it to Vulkan `R16G16_SFLOAT`; the viewport/scissor supplies the
height passed to the decoder because `SURFACE_INFO` does not encode one. The
capture's mode-6 source format 12 (`2_10_10_10_FLOAT_AS_16_16_16_16`) maps to
the existing `R16G16B16A16_SFLOAT` representation in the raster decoder.
However, this capture uses mode 6, so its copy source is not yet routed through
that raster path. The mappings follow the [Xenos format definitions](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/xenos.h)
and [Xenia's Vulkan target mapping](https://github.com/xenia-canary/xenia-canary/blob/canary_experimental/src/xenia/gpu/vulkan/vulkan_render_target_cache.cc).

The draw-input regression checks the captured format-6 tuple and format-12
mapping. The Vulkan regression renders a synthetic draw to `R16G16_SFLOAT`,
then runs the existing captured sample-zero Copy/Convert path. Native Linux
tests passed 4/4 and plugin tests passed 7/7 with Vulkan validation forced.
The ARM64 offscreen checker also passed on the Redmi Note 8 Pro Mali-G76 MC4
using Vulkan 1.1.131. The updated Android plugin compiled but was not installed
over the running retail app; the game stayed at the disclaimer with the same
PID and screenshot hash before and after the offscreen check.

This adds target-format handling, cached intermediate images, ordered
submission for compatible segments, same-layout EDRAM persistence, and one
exact format-31 guest-fetch consumer path, plus tiled base-level format-31
guest-memory upload. EDRAM alias reinterpretation, guest-memory writeback,
independent guest-texture endian verification, and complete color/depth clear
side effects remain unimplemented. The captured transition is still blocked by
source association and target-layout aliasing.
Detailed captured values, build identities, tests, and limits are in
[`process2_redmi_xenos_16bit_targets_20261026.json`](../../evidence/process2_redmi_xenos_16bit_targets_20261026.json).

## Captured offscreen raster extents (2026-10-27)

The transition capture's single-sample `16_16_FLOAT` downsample targets use
surface pitches 320, 160, and 80 while their top-left viewport/scissor heights
are 243, 81, 27, 9, 3, and 1. The ring frontend previously scaled target height
from the 1280x720 guest output, which estimated 180 for the 320-pixel pitch
and clipped the captured 243-pixel draw. For a single-sample target whose pitch
differs from the guest output and whose captured viewport starts at the origin,
the frontend now derives the minimum height from the viewport and scissor. The
existing guest-output aspect fallback remains for other target forms.

The draw-input regression checks all seven captured extents. Native CTest passed
4/4 with Vulkan validation; Linux plugin CTest passed 7/7 with validation. The
same ARM64 draw-input executable passed on the Redmi Note 8 Pro. The updated
Android plugin builds for AArch64 / Android API 26, but was not installed over
the running game. The app stayed at the disclaimer with PID 14611, and its
before/after screenshot hashes match. This corrects target sizing for capture
parsing and preparation; it does not execute the ordered mode-6 copies or
verify a changed retail image. See
[`process2_redmi_offscreen_raster_extents_20261027.json`](../../evidence/process2_redmi_offscreen_raster_extents_20261027.json).

## Redmi bounded PM4 expansion and retail Bink frame (2026-10-27)

The indirect-buffer expander's packet cap increased from 262,144 to 1,048,576.
The 64 MiB root-stream limit, 256 MiB expanded-byte limit, 4,096 indirect
buffer limit, and depth-8 nesting limit remain unchanged. A regression expands
262,145 one-dword NOP packets, just above the old cap. The prior Redmi log had
two `expanded Xbox PM4 packet limit exceeded` drops; the updated Android P2
plugin ran for over seven minutes with 1,138 presenter submissions and no
packet-limit or malformed-batch errors. This removes that rejection class;
the before/after runs do not prove that it alone caused the older session to
stop progressing.

The candidate APK replaced only the two P2 Vulkan plugin aliases and preserved
the installed runtime DSO. It was v3-signature verified and 16 KiB aligned,
then installed with `adb install -r` so game data remained intact. On the Redmi
Note 8 Pro / Mali-G76 MC4 the game passed the language selector after one
default-English A event. No input was sent on or after the disclaimer. The
live log contains 319 four-draw batches from 03:52:08.893 to 03:52:49.920; a
phone frame from this sequence correlates with the original retail
`Franchise_Ident.bik` at source time 0.9 s with grayscale correlation 0.9236.
That proves a real Bink frame reached the Vulkan presenter, not full clip or
audio parity. The clip probes as 1280x720 Bink video, 29.97 fps, 9.376 s, and
its SHA-256 matches the previously inspected retail file. The game then showed
the readable legal disclaimer; it remained there at the final capture.

One 14-draw transition at 03:53:25 failed closed because draw 1 changes the
Xenos target layout from 2560x1440 / 4x / format 3 / depth base 1024 / pitch
1280 to 1280x720 / 4x / format 0 / depth base 720 / pitch 640. Thirteen-draw
presenter batches continued afterward. Ordered EDRAM targets and intermediate
mode-6 copy writes remain the next graphics gap; the observed failure is not
evidence that they caused the later guest-state stop.

The host native suite passed 4/4 with `VK_LAYER_KHRONOS_validation`, the Linux
P2 plugin suite passed 7/7 with the layer, and the Android ARM64 ring regression
passed on the phone. APK/plugin hashes, the complete rotated phone log, the
matched retail frame, and scope limits are in
[`process2_redmi_pm4_packet_limit_20261027.json`](../../evidence/process2_redmi_pm4_packet_limit_20261027.json).

## Ordered captured draw and copy operations (2026-10-27)

The ring frontend now passes a frame-local operation stream alongside the
prepared draw resources. It retains packet order for prepared draws, recognized
Copy/Convert operations (including their captured destination state and source
extent and raw source surface/color/depth/mode registers), and unresolved draw
packets. The Vulkan renderer checks that draw references remain ordered and
complete, and includes the captured sequence in target-layout, copy-extent,
and mixed-sample failure diagnostics. The host renderer regression exercises
Draw → Copy/Convert → Draw, preserves the raw mode-6 source-target registers,
rejects reordered draw references and packet ordinals, and rejects incomplete
copies and unresolved draws.

When ring tracing is enabled, each PM4_INTERRUPT is also logged with its ring
generation, batch read/write pointers, expanded packet ordinal, source IB and
byte offset, CPU mask, dispatched CPU mask, and each asserted CPU's guest
callback address, callback data, and dispatch status. Status distinguishes a
missing callback or host context, wrong host thread, successful return from
`ExecuteInterrupt`, and an exception. This helps distinguish multiple guest
interrupt packets from multiple callbacks requested by one packet; it does not
coalesce interrupts.

The ordered executor now retains same-layout color/depth targets between
segments and can execute a copy-only packet from an initialized target when
the captured source layout matches exactly. A later texture fetch may consume
an intermediate format-31 Vulkan image only when its linear, base-level
descriptor exactly matches a preceding format-31 Copy/Convert destination
(guest address, extent/pitch, number format, endian, sample selection, and
conversion flags). In that case the renderer samples the cached
`R16G16_SFLOAT` image and does not read stale guest RAM. The regression checks
that result against a separate upload of the same half-float values; it is a
synthetic data-flow test, not a retail frame.

The captured 14-draw transition still does not execute end to end. Its draw
#12 texture descriptor is tiled and requests a mip range, and its address
does not exactly match the preceding format-31 destination, so this narrow
cache path rejects it. EDRAM alias reinterpretation across changed target
layouts, clear side effects, depth/stencil preservation through the full
sequence, and broader texture subresource mapping remain unsupported. The
host Vulkan suite passed 4/4 with Khronos validation. The Android renderer
regression was rebuilt for ARM64/API 29 and passed on the Redmi Note 8 Pro's
Mali-G76 MC4 with Vulkan 1.1.131, including the ordered format-31
Copy-to-texture cache test. Android has no Khronos validation layer in this
run. A final draw-only presenter stage now retains requested output readback
even when the PM4 stream has no presenter Copy/Convert packet; the existing
synthetic live-ring readback test caught and verifies this path. The complete
Linux ReXGlue plugin DSO linked, and its six plugin CTests passed with
`VK_LAYER_KHRONOS_validation`. The DSO SHA-256 is
`068886f84ce1557cfdc8a536a599215d74658342a6551405ce22de779f70107f`.
The current Android plugin translation unit compiled with NDK r28c, but the
Android plugin DSO was not linked or installed. These synthetic checks do not
claim retail parity. Build and test details are in
[`process2_ordered_operation_stream_20261027.json`](../../evidence/process2_ordered_operation_stream_20261027.json).
The follow-up preflight regressions and per-CPU interrupt callback trace fields
are recorded in
[`process2_ordered_edram_interrupt_trace_progress_20261027.json`](../../evidence/process2_ordered_edram_interrupt_trace_progress_20261027.json).

## Mode-6 source registers and PM4 interrupt trace (2026-10-27)

The operation stream now retains the raw Xenos source surface, color, depth,
and mode registers for every recognized Copy/Convert packet. This captures the
mode-6 source contract seen in the 14-packet disclaimer-to-video transition
failure (`surface_info=0x14020500`, `color_info=0xC0000`, `depth_info=0x400`,
`mode_control=6`) for the next ordered-copy implementation step.

When ring tracing is enabled, PM4_INTERRUPT diagnostics include each packet's
generation, batch pointers, expanded packet ordinal, source IB and byte offset,
CPU mask, and dispatched CPU mask. P2 dispatches once per asserted CPU bit and
does not retry or coalesce callbacks. The supplied P1 watchpoint lacks the
packet masks and identities needed to attribute its two callback entries; no
interrupt fix or retail-video causality claim is made here.

The native Vulkan tests passed 4/4 and the Linux plugin tests passed 7/7 with
Khronos validation enabled. The Android plugin was not rebuilt or installed in
this iteration, and the active Redmi game was left running on the disclaimer.
Evidence and limits are in
[`process2_mode6_sources_and_interrupt_trace_20261027.json`](../../evidence/process2_mode6_sources_and_interrupt_trace_20261027.json).

## Extended PM4 interrupt trace window (2026-10-27)

The opt-in ring trace now retains up to 8,192 `PM4_INTERRUPT` records per
plugin lifetime (previously 128). Each record keeps the ring guest address,
source and generation, batch pointers, expanded packet ordinal, packet source
and byte offset, requested/dispatched CPU masks, and every asserted CPU's
callback address, callback data, and status. A single warning marks the cap.
No interrupt dispatch or guest-runtime behavior changes; with
`SHIFT_NATIVE_VULKAN_TRACE_RING=0`, interrupt trace formatting and its counter
remain untouched. The live-ring smoke has explicit trace-on and trace-off
checks.

The last capture recorded 128 interrupts in 4.2 seconds before reaching the
old cap, about 30 records/second. The new bound has capacity for that observed
rate across more than four minutes, including the requested 40–50 second
post-Bink window. A new retail run is still required to confirm its actual
interrupt rate and capture the queue/event/counter interval. See
[`process2_interrupt_trace_window_20261027.json`](../../evidence/process2_interrupt_trace_window_20261027.json).

## WAIT_REG_MEM backing and packet join (2026-10-27)

Memory-mode `WAIT_REG_MEM` validates the physical guest span, obtains its word
through `memory_->TranslatePhysical`, and polls that word with an acquire
atomic load. `GpuSwap` converts the raw guest value for the packet's endian
mode. This branch does not read or update a renderer-side shadow; only the
separate `COHER_STATUS_HOST` branch uses renderer-owned status state. The
bounded WAIT sample now includes the ring generation and batch pointers, ring
guest address, expanded packet ordinal, indirect-buffer source/depth/offset,
physical guest wait address, raw and endian-adjusted values, and the backing
reader label. The live-ring trace regression checks that join tuple. This
identifies what Process 2 reads, but it does not identify which guest CPU or GPU
writer produced a value transition. The Redmi v38 CPU watchpoint result and
the one-record interrupt-count discrepancy remain un-attributed; see
[`process2_wait_reg_mem_packet_join_20261027.json`](../../evidence/process2_wait_reg_mem_packet_join_20261027.json).

## Exact Process 1 runtime build (2026-10-27)

For a reproducible Linux trace build, CMake accepts a prebuilt-runtime
integration when the matching older SDK keeps the Vulkan provider in
`rexruntime` rather than defining a separate `rexui-vulkan` target. The
instrumented DSO was factory-smoke-tested and has no unresolved symbols. It is
built against the exact Process 1 runtime and host/XEX identity, with bounded
ring tracing enabled by default. The DSO has been handed to Process 1 for a
same-run capture; callback attribution remains pending that run. See
[`process2_p1_exact_pm4_trace_plugin_20261027.json`](../../evidence/process2_p1_exact_pm4_trace_plugin_20261027.json).

## Redmi disclaimer follow-up and ARM64 renderer check (2026-10-27)

The user confirmed that the legal disclaimer advances automatically and does
not require a button press. No input was sent. During the follow-up, the active
Redmi process remained in the foreground on the same disclaimer screenshot.
Its 04:36:49–04:38:14 device-log window contains 145 successful submissions of
13 captured draws and 145 accepted final presenter copies, with no logged
`WAIT_REG_MEM` false samples or Vulkan refresh failures. This does not establish
why the game has not submitted a video frame.

The current source also built the ARM64 Vulkan renderer checker with NDK r28c,
Android API 26, and passed the draw-input, guest-ring, shader-translation, and
offscreen renderer checks on the Redmi Mali-G76 MC4 / Vulkan 1.1.131. The
renderer check uses synthetic draw shaders and does not replay the retail
transition. The game APK and loaded plugin were not changed; its PID and
screenshot hash remained unchanged. Device log hash, binary hashes, and exact
limits are in
[`process2_redmi_disclaimer_followup_arm64_check_20261027.json`](../../evidence/process2_redmi_disclaimer_followup_arm64_check_20261027.json).

## Retail transition shader MIN instruction (2026-10-27)

The Redmi transition log reports an unsupported Xenos vector ALU opcode 3 at
pixel-shader instruction 12. Opcode 3 is component-wise MIN; the translator now
emits the captured `src0 < src1 ? src0 : src1` selection and has a regression
for its vector result and destination mask. The selection also keeps Xenos'
operand choice when a comparison is unordered.

The native Vulkan suite passed 4/4 and the Linux plugin suite passed 7/7 with
Khronos validation enabled. The ARM64 shader-translation checker passed on the
Redmi Note 8 Pro. The running game was not restarted or modified; its PID and
screenshot hash stayed unchanged. This closes one shader translation case,
not the captured transition: its 14-draw frame still fails on changing Xenos
target layouts, and other shader/resource errors remain. No retail video frame
or parity result is claimed. Details and limits are in
[`process2_retail_transition_min_alu_20261027.json`](../../evidence/process2_retail_transition_min_alu_20261027.json).

## Conditional Xenos shader execution (2026-10-27)

The same Redmi transition log rejects draw 2 with an unsupported shader
control-flow opcode, but the raw shader bytes were not retained, so that log
does not identify the opcode. The bounded decoder and translator now support
Xenos `CEXEC` and `CEXECE` (opcodes 3 and 4) when their condition is captured
as `b128` or `b129`. `CEXECE` ends shader execution only when its condition is
true, matching the documented Xenos behavior. The source encoding is cross
checked against [Xenia's Xenos ucode definitions](https://raw.githubusercontent.com/xenia-project/xenia/master/src/xenia/gpu/ucode.h).
Other control-flow opcodes now report their numeric opcode and instruction
slot, so a later retail trace can identify the next unsupported form.

Synthetic regressions check CEXEC field decoding, true/false CEXEC fallthrough,
and true/false CEXECE termination. Native Vulkan CTest passed 4/4 and Linux
plugin CTest passed 7/7 with `VK_LAYER_KHRONOS_validation` forced. The ARM64
shader-translation check also passed on the Redmi Note 8 Pro / Mali-G76 MC4.
Only the test binary was uploaded; the game remained at the disclaimer with
the same PID and screenshot hash. This change may cover the rejected opcode if
draw 2 used CEXEC/CEXECE;
it does not prove that mapping or advance the game. The raw shader is absent,
and the transition still has separate texture-descriptor, branch-predicate,
and changing-target-layout failures. Build identities and exact evidence are
in [`process2_retail_cond_exec_20261027.json`](../../evidence/process2_retail_cond_exec_20261027.json).

## Vulkan coherency wait fast path (2026-10-27)

The active Redmi log recorded 22 submissions of the same 13-draw disclaimer
batch and 467 completed `COHER_STATUS_HOST` waits over 12.4 seconds (about 21
wait completions per submitted batch). The renderer cache now exposes an
atomic in-flight-frame count. The P2 ring worker skips the synchronous UI-thread
handoff only when that count is zero; a nonempty queue still receives the full
fence drain. This avoids empty repeated handoffs without changing queued Vulkan
work or presenting synthetic output.

Linux CTest passed 4/4 with the Khronos validation layer forced on the GTX 950.
The Android ARM64 plugin compiled for API 26, and the renderer/cache regression
passed on the Redmi Mali-G76 MC4. The installed APK remains unchanged: updating
it failed with `INSTALL_FAILED_INSUFFICIENT_STORAGE` despite 1.3 GiB free, so
the live process did not exercise the plugin fast path. The disclaimer screenshot
and PID remained unchanged, and no input was sent. No live speedup or automatic
transition is claimed. See
[`process2_redmi_coherency_wait_coalescing_20261027.json`](../../evidence/process2_redmi_coherency_wait_coalescing_20261027.json)
for hashes and limits.

## Raw Xenos render-target format in EDRAM layout checks (2026-10-27)

The Redmi transition capture includes `RB_COLOR_INFO.COLOR_FORMAT=12`
(`color_info=0x000C0000`). The renderer maps it and format 3 to the same
Vulkan attachment format, so target-layout checks now also retain and compare
the raw guest format. EDRAM sample addressing uses the Xenos storage width:
the decoder-supported format 12 follows the 32bpp sample layout, while true
64bpp Xenos formats remain rejected by the address helper. This distinction is
cross-checked against [Xenia's format definitions](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/xenos.h).

The Linux regression checks format-12 sample, tile-row, and wrap addresses,
true 64bpp rejection, and two raw formats that share one Vulkan format. This
also builds `rexgpu-shift-native` against ReXGlue 0.10.0 with Clang. Although
same-layout EDRAM targets now persist across submissions, this does not execute
the captured transition end to end; the 14-draw sequence still cannot be
presented as retail parity. Details and validation results are in
[`process2_xenos_guest_color_format_contract_20261027.json`](../../evidence/process2_xenos_guest_color_format_contract_20261027.json).

## Android renderer fixtures and runtime-matched factory smoke (2026-10-27)

The Android renderer-check target now compiles the four gamma SPIR-V inputs
used by its ordered Copy/Convert regression. Native Linux CTest passed 4/4
with `VK_LAYER_KHRONOS_validation`; the Android draw-input and synthetic
offscreen Vulkan checks passed again on the Redmi Note 8 Pro / Mali-G76 MC4
with Vulkan 1.1.131.

An ARM64 plugin built against the ReXGlue 0.10.0 Android SDK snapshot used by
the installed runtime passed isolated `dlopen`, ABI-version and graphics-factory
checks on the phone. The factory returned a graphics object without a
presentation surface. A plugin built against a newer SDK separately crashed
inside the runtime during `dlopen`; the root cause is not established. Neither
plugin was installed into the game. The app APK and data were left unchanged,
and no game process was running during the check. These tests do not replay the
retail 14-draw transition, verify swapchain presentation, or establish retail
parity. See
[`the evidence record`](../../evidence/process2_android_shader_fixtures_factory_smoke_20261027.json).

## Original PM4 geometry for ordered Copy/Convert (2026-10-27)

Recognized rectangle-list Copy/Convert packets now preserve their actual
translated Xenos vertex shader, vertex constants, decoded index data, guest
vertex-fetch payload, and source raster/scissor. Ordered Vulkan replay binds
that geometry with the captured format-specific resolve fragment shader;
missing geometry fails closed instead of silently drawing a fullscreen
triangle. Cached copy destinations load prior contents on later partial
writes. Packet diagnostics report topology, index count, and captured buffer
sizes. The fail-closed layout mismatch diagnostic now prints the active draw
and Copy source EDRAM fields so the next retail trace can distinguish an
initialized prior target from an alias that requires physical EDRAM transfer.

Native Linux CTest passed 4/4 with `VK_LAYER_KHRONOS_validation`; the Linux
ReXGlue plugin CTest passed 6/6 with the same layer. The ARM64/API 26 guest
ring, Vulkan renderer core, and renderer-check target compiled with NDK r28c;
the renderer-check was compile-only and the Android plugin translation unit
was not rebuilt in this verification run. The rebuilt Linux plugin SHA-256 is
`e9c5873adac7dd14695ae586dac89fad04a7e935e54c5dc58a6fa5f8f0981e7e` (Build ID
`58ecafd975cc745cffbb027c2267aa3c17aac98a`). A previous full Android plugin
link attempt stopped in the external ReXGlue SDK at `fiber_posix.cpp`
(`getcontext`, `makecontext`, and `swapcontext` are not declared by that NDK
build). ADB currently lists no device, so this version has not been exercised
on the phone. The Vulkan regression uses synthetic indexed rectangle geometry,
checks that missing geometry is rejected, and verifies that a zero-area
captured scissor preserves an initialized non-black destination. It also
checks that a Copy source-layout rejection reports both active and source
EDRAM layouts. It does not establish retail Copy/Convert pixel parity.

P1's v42 capture supplied the exact source layout for Copy/Convert packet 49.
The renderer now handles that one captured sample-zero 4x-to-1x view; other
EDRAM layout aliases remain fail-closed. The 14-draw transition is not replaying
fully. The resolve fragment shader is still an explicit implementation of the
decoded Copy state, not a verified retail image match. PM4 interrupt to guest
callback attribution also remains incomplete. Build identities, checks, and
limits are recorded in
[`process2_ordered_copy_geometry_capture_20261027.json`](../../evidence/process2_ordered_copy_geometry_capture_20261027.json).

## Captured packet-49 sample-zero source view (2026-10-27)

P1's v42 same-run trace shows packet 24 drawing to color base `0x0`, depth
base `0x2d0`, extent 1280x720, pitch 640, 4x MSAA, and RGBA8 gamma. Copy/Convert
packet 49 then selects source 0/sample 0 and describes that same base and extent
as pitch 1280, 1x, RGBA8 linear; it converts to format 6 at `0x0975E000`.
The renderer now accepts only this exact observed case and executes the captured
Copy rectangle with the existing 4x `sampler2DMS` path at sample index 0. Other
non-matching EDRAM source layouts still fail closed. When a later draw changes
layout before a Copy boundary, the diagnostic now prints both packet ordinals
and full target layouts for the next trace.

The renderer regression feeds the same captured-shaped draw/copy pair through
the ordered executor and direct Vulkan submission and requires identical
readback. Native Linux CTest passed 4/4, plugin CTest passed 6/6, both with
`VK_LAYER_KHRONOS_validation`; the Android ARM64/API 26 renderer core also
compiled. Linux plugin SHA-256 is
`4feb8ba496b625a578205f2c0b09a7b73e9ea54ecc9af2b36a42ee4184ff91d7`, Build ID
`563c64eb612333d04d54df1f08fba302e9ab5b12`.

This only validates ordered submission equivalence inside the renderer; it
does not prove the selected Vulkan sample matches Xenos EDRAM addressing or a
retail pixel. The v42 capture used the preceding plugin build, and this change
has not yet been replayed against the game. Its next recorded blocker is draw
packet 25 changing target layout before Copy packet 53. The full transition,
depth/stencil preservation across layout changes, and interrupt/callback join
remain open. See
[`process2_packet49_sample0_edram_view_20261027.json`](../../evidence/process2_packet49_sample0_edram_view_20261027.json).

## Captured packet-24 to packet-53 mixed-sample segment (2026-10-28)

P1's v44 run exposed the exact next draw boundary: packet 24 targets 1280x720
RGBA8 gamma at color base `0x0`, depth base `0x2d0`, pitch 640 and 4x MSAA;
packet 25 keeps those bases and extent but switches to pitch 1280 and 1x. The
ordered segment then contains draws 26–28 and Copy/Convert packet 53. That copy
uses source 0/sample 0, the same target bases, a 1x pitch-1280 source view, and
writes format 6 to `0x0975E000` using its captured rectangle geometry. Packet
49 passed its prior source-layout guard in this v44 run. The capture and its
raw-log hash are recorded in
[`process2_packet24_to_53_ordered_mixed_sample_20261028.json`](../../evidence/process2_packet24_to_53_ordered_mixed_sample_20261028.json).

The ordered executor now routes only the same-base, same-depth-base, same-
format, same-extent RGBA8 gamma 4x-to-1x transition with exactly doubled pitch
through the existing mixed-sample Vulkan submission path. The path resolves
the 4x color attachment to its 1x attachment before submitting the subsequent
1x draws and captured Copy 53 geometry; a near-match pitch of 1272 remains
rejected. This is a candidate translation of the observed operation order:
Vulkan's ordinary color resolve has not been shown to reproduce Xenos EDRAM
sample/backing semantics. The synthetic regression proves ordered/direct
executor readback equality only, not retail image parity.

The same v44 run also had a separate 14-draw refresh that stopped at packet 1:
it changed from the packet-0 RGBA8 gamma view to a depth-only RGBA8 linear view
with identical color/depth bases, extent, pitch 640, 4x samples, and depth
format. The ordered path now allows that exact depth-only view only when its
color write mask is zero, keeping it on the shared render pass and depth
attachment. Other depth-only aliases remain rejected. A synthetic Draw/Draw/
Copy regression exercises the shared depth target, but retail depth contents
and the rest of the 14-draw package have not yet been verified.

Native Linux tests passed 4/4 and plugin tests passed 6/6 with
`VK_LAYER_KHRONOS_validation`. The Android ARM64/API 26 renderer core and
regression executable compiled, but no device was attached for execution. P1
has the new Linux DSO path, SHA-256, and Build ID for a same-run retail replay.
The full 14-draw operation package, intermediate target persistence, retail
readback, and presentation remain unverified. The v44 source-1 interrupt trace
now has a continuous timestamp/order join for all 962 P1 callback records to
P2 PM4 interrupt IDs 1101–2062; callback target and CPU wrapper addresses are
different layers, so payload-level guest equivalence remains open.

## v45 mixed-sample depth-only target views (2026-10-28)

P1's v45 same-XEX capture shows two additional ordered layout changes on the
same `0x0` color / `0x2d0` depth bases and 1280x720 extent. One stream reaches
draw 29 after a 1x gamma, pitch-1280 draw, then switches to a depth-only 4x,
pitch-640 view before Copy/Convert packet 54. Another stream begins in a
depth-only 4x, pitch-640 view and changes to a gamma 1x, pitch-1280 view at draw
26 before packet 72. The retained run log records both transitions, but does
not include the per-draw color mask, depth/stencil enables, or stencil write
mask; see
[`process2_v45_depth_only_4x_transition_20261028.json`](../../evidence/process2_v45_depth_only_4x_transition_20261028.json).
The same run's interrupt trace has an ordered timestamp join for all 881 P1
source-1 callback rows to P2 PM4 interrupt IDs 969–1849 (0–77 ms delta,
0x04 CPU mask). The final P2 event is 8 ms beyond the P1 callback time window;
P1 records registered guest callback targets while P2 records the outer CPU
wrapper, so payload-level equivalence remains unproven. The full row-by-row
packet ordinal, ring generation, read/write pointers, and callback mapping is
in [`process2_v45_source1_interrupt_join_20261028.json`](../../evidence/process2_v45_source1_interrupt_join_20261028.json).

The ordered executor now accepts only these captured gamma/depth-only aliases:
matching bases, extent, depth format, a nonzero gamma color write mask, and a
zero depth-only color write mask, with either
the same 4x pitch or a 1x gamma pitch exactly twice the depth-only 4x pitch.
For Copy/Convert source matching, it tracks the most recent color-writing draw
so an initial depth-only view does not hide the later 1x gamma source. The
existing mixed-sample executor still rejects a trailing 4x draw that writes
color and requires the provider-confirmed Vulkan depth/stencil resolve when a
4x depth/stencil result feeds a later 1x test. Unmatched pitches and bases
remain fail-closed.

Synthetic captured-shaped regressions cover both transition directions,
Draw/Copy ordering, readback equality between direct and ordered Vulkan paths,
and an unmatched packet-29 pitch. Linux renderer CTest passed 4/4 and plugin
CTest passed 6/6 with `VK_LAYER_KHRONOS_validation`; the Android ARM64/API 26
renderer and check executable compile. These are routing/executor checks, not
retail image parity. P1's v45 run used the preceding plugin build and stopped
before exercising this change; the new build has not yet been replayed. The
full EDRAM backing/sample mapping and the captured packets' actual depth/stencil
effects remain unverified because that run did not retain their raster flags.
No Android device was attached for this build.
