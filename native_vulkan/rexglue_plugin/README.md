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

The supported path is deliberately narrow: triangle-list DMA-indexed
`DRAW_INDX` and `DRAW_INDX_2`, the captured FLOAT3 vertex fetch and format-6
texture, the captured shader pair (pointer-loaded or inline
`IM_LOAD_IMMEDIATE`), the captured raster register set, and the captured blend
control. Unsupported draw state is rejected. The frame path clears the
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
cases. The platform-independent Vulkan core also has an offscreen indexed-draw
smoke. It passed with Vulkan validation on NVIDIA GeForce GTX 950, and on
Redmi Note 8 Pro (Mali-G76 MC4) using Vulkan 1.1. Those smoke shaders are
synthetic and verify pipeline/resource/layout operations only; they are not
retail output evidence.

On 2026-10-23, the retail Linux executable was run with `--gpu_plugin=shift-native`.
The runtime mapped this plugin without mapping `rexgpu-xenos`, initialized the
guest ring at `0x09752580`, and the worker consumed four live batches (1,828
PM4 packets) containing two `XE_SWAP` packets. This verifies the plugin is
connected to the retail guest's PM4 path. A later opcode-only audit counted
100 `DRAW_INDX_2` and 14 `IM_LOAD_IMMEDIATE` packets, but did not retain their
raw words; it cannot establish that the draws use DMA indices or that the
inline shader payloads are valid. That run submitted zero Vulkan frames, so a
retail draw through the plugin is still unconfirmed. The current worker logs
one bounded raw packet sample for each opcode on its next live run. See
[`process2_xbox_live_guest_ring_20261023.json`](../../evidence/process2_xbox_live_guest_ring_20261023.json).

The earlier one-draw capture bundle remains separate evidence for the project
renderer, not proof of a complete scene.

On Android NDK r28.2 / API 33, `rexui-vulkan` and the Android surface/window
sources compile for arm64. Building the full plugin then stops in ReXGlue's
POSIX fiber backend because Android Bionic does not provide
`getcontext`/`makecontext`/`swapcontext`. That scheduler code belongs to
Process 1. The game project also has no Android Activity or APK target yet, so
the Redmi Note 8 Pro checks cover the offscreen Vulkan renderer only, not a
full game build. The parser, guest-ring, shader-translation, and renderer
checks were rebuilt for API 33 and rerun on the device; the renderer test uses
synthetic shaders and does not show a retail frame.
