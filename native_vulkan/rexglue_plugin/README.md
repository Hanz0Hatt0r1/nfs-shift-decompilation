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
draws and AutoIndex point-list `DRAW_INDX_2` draws, including the observed
vertex shader with no fetch inputs. It translates the captured shader pair
(including inline `IM_LOAD_IMMEDIATE`), validates required constants, and
resolves supported vertex and texture resources. Rectangle-list AutoIndex
draws and unsupported raster/resource forms are rejected. The frame path clears the
presenter image and renders the collected draws; it does not reconstruct Xenos
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

The platform-independent Vulkan core also has a synthetic offscreen AutoIndex
point-draw smoke with no vertex attributes or vertex buffer.
It passed with Vulkan validation on NVIDIA GeForce GTX 950, and on Redmi Note 8
Pro (Mali-G76 MC4) using Vulkan 1.1. Those smoke shaders are synthetic and
verify pipeline/resource/layout operations only; they are not retail output
evidence.

On 2026-10-23, a headless retail Linux run with `--gpu_plugin=shift-native`
mapped this plugin without mapping `rexgpu-xenos`, initialized the guest ring
at `0x09752580`, and consumed 1,828 PM4 packets with two `XE_SWAP` packets.
The retail stream contained 100 AutoIndex draws (96 points and four rectangle
lists), with no DMA-indexed draw observed. A later run with the updated plugin
translated and resolved 24 point-list draws at each of two swaps, then
submitted both 1280x720 frames to the Vulkan presenter. The same ring contained
the 108-byte full/mini-fetch VS; the plugin translated it, but the rectangle
list that uses it remains unsupported. This is the first confirmed live retail
Vulkan submission. It does not verify visible output pixels, scene parity,
EDRAM accumulation, or Vulkan validation-layer behavior for the retail frame.
See
[`process2_xbox_live_guest_ring_20261023.json`](../../evidence/process2_xbox_live_guest_ring_20261023.json).

An earlier Gamescope headless retry used info-level logging and recorded no
draw submission; the later debug run above supersedes that result.

The earlier one-draw capture bundle remains separate evidence for the project
renderer, not proof of a complete scene.

On Android NDK r28.2 / API 33, `rexui-vulkan` and the Android surface/window
sources compile for arm64. Building the full plugin then stops in ReXGlue's
POSIX fiber backend because Android Bionic does not provide
`getcontext`/`makecontext`/`swapcontext`. That scheduler code belongs to
Process 1. The game project also has no Android Activity or APK target yet, so
the Redmi Note 8 Pro checks cover the offscreen Vulkan renderer only, not a
full game build. The Android arm64 CI now builds the project Vulkan renderer
smoke and publishes its executable plus Vulkan 1.1 SPIR-V inputs. On 2026-10-23
the artifact from [CI run 39938067570](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/actions/runs/39938067570)
ran on the connected Redmi Note 8 Pro (Android API 33, Mali-G76 MC4):
`synthetic offscreen Vulkan 1.1 AutoIndex point draw passed on Mali-G76 MC4`.
The device test
used synthetic shaders and ran without the validation layer; it does not show
a retail frame. The parser, guest-ring, shader-translation, and renderer
checks were also rebuilt for API 33 and rerun on the device.
