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
existing ReXGlue 0.10.0 Android build has a monolithic `rexui` target, so the
plugin uses its exported Vulkan provider through `rexruntime`; with that older
provider API it does not request geometryShader and rejects rectangle-list
draws, while point-list draws remain available. With the split `rexui-vulkan`
target, the plugin requests geometryShader independently and can submit the
captured rectangle-list form when the device supports it. Debug builds stage
`librexgpu-shift-natived.so`, matching the host plugin loader's debug suffix.

The host app must select the `shift-native` plugin through its existing
`gpu_plugin` setting. An Android activity argument alone is insufficient if
the app's `OnPreSetup` hook overwrites that setting. This integration does not
change the app-owned startup hook.

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
content, Android game integration, or scene parity. Xenos EDRAM accumulation,
frontbuffer resolution, other raster/resource states, and Vulkan validation
for a live retail frame remain unverified.

The first 73-packet startup batch contains 24 point draws before the captured
vertex-shader control register is available, so those draws are skipped. Later
ring batches provide the required state and submit the supported draws. This
ordering is preserved in the logs rather than hidden by synthesized defaults.

The earlier one-draw capture bundle remains separate evidence for the project
renderer, not proof of a complete scene.

On Android NDK r28.2 / API 33, `rexui-vulkan` and the Android surface/window
sources compile for arm64. Building the full plugin then stops in ReXGlue's
POSIX fiber backend because Android Bionic does not provide
`getcontext`/`makecontext`/`swapcontext`. That scheduler code belongs to
Process 1. The repository also builds a minimal Android NativeActivity surface
probe, but it does not integrate the game or ReXGlue runtime and has no game
manifest/APK target. The Redmi Note 8 Pro checks cover the offscreen Vulkan
renderer and parser only, not a full game build. The Android arm64 CI builds
the project Vulkan renderer smoke and publishes its executable plus Vulkan 1.1
SPIR-V inputs. The earlier artifact from
[CI run 39938067570](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/actions/runs/39938067570)
passed the original renderer smoke on this phone. For the readback update, we
rebuilt the test locally for Android arm64 and ran it on the connected Redmi
Note 8 Pro (Android API 33, Mali-G76 MC4):
`synthetic offscreen Vulkan 1.1 AutoIndex point draw and output readback passed
on Mali-G76 MC4`. This device test uses synthetic shaders and ran without the
validation layer; it does not show a retail frame. Temporary device files were
removed. The parser, guest-ring, shader-translation, and renderer checks were
also rebuilt for API 33 and rerun on the device.

A fresh build from the current Process 2 checkout (`699b38a7`) used NDK
r28.2 with `ANDROID_ABI=arm64-v8a` and `ANDROID_PLATFORM=android-29`. On
2026-10-23, `shift_xbox_draw_input_check`, `shift_xbox_guest_ring_check`,
`shift_xbox_shader_translate_check`, and
`xbox_live_vulkan_renderer_check` all exited successfully on the connected
Redmi Note 8 Pro (Android API 33, Mali-G76 MC4). The renderer check submitted
its synthetic Vulkan 1.1 AutoIndex point draw and verified output readback.
This current-source device run covers the ARM64 parser, translator, and
project renderer core; it did not load the ReXGlue plugin or run the retail
guest ring. The full Android game build remains blocked by the runtime fiber
backend and missing game Activity/APK integration described above.

Using the same NDK/API29 configuration, the current
`shift_native_gpu_plugin.cpp` translation unit also compiled by itself for
`aarch64-none-linux-android29` (exit 0). This isolates the renderer-owned
plugin source from the full SDK link. Clang emitted one non-fatal warning in
the SDK header `rex/platform/fpscr.h` about the ARM64 `fpcr` inline-assembly
operand width. This was a translation-unit compile only: it did not link the
ReXGlue runtime or run a game.

The guest-ring path now decodes the captured `PM4_INTERRUPT` CPU mask and
dispatches the registered GPU callback through a ReXGlue `XHostThread`, so the
callback has a guest thread context. The callback is issued after the current
ring batch is consumed and its read pointer is published; exact ordering at
each interrupt packet inside a batch is not verified. The decoder regression
and Android API 33 guest-ring smoke passed on Redmi Note 8 Pro (Mali-G76 MC4),
and the Linux plugin suite passed 3/3 with the readback regression also passing
under Vulkan validation. These are parser/plugin checks, not a full Android
game test.
The current-source Linux rerun described above also consumed the captured
interrupts and dispatched callbacks. See the
`gpu_interrupt_routing_update` and `post_scalar_destination_live_rerun` entries
in the evidence JSON for the build and test details.
