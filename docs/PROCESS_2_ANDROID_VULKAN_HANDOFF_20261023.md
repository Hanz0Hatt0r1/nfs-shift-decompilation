# Process 2 Android Vulkan handoff (2026-10-23)

## Boundary already implemented

The Android Activity does not need to create or pass a `VkSurfaceKHR` to the
SHIFT renderer. ReXGlue's `rexui-vulkan` presenter owns the platform surface
and swapchain. On Android, `WindowSDL` obtains the current `ANativeWindow`
from SDL's `SDL_PROP_WINDOW_ANDROID_WINDOW_POINTER`; the presenter enables
`VK_KHR_surface` and `VK_KHR_android_surface`, calls
`vkCreateAndroidSurfaceKHR`, and chooses a queue family that supports both
graphics and presentation.

The plugin's existing handoff is:

1. `SetupPresentation(WindowedAppContext*)` creates
   `VulkanProvider::Create(false, true)` and creates the presenter on the UI
   thread through `CallInUIThreadSynchronous`. The Android UI loop must keep
   pumping the context's queued UI work. The first argument disables
   ReXGlue GPU emulation; this provider/presenter is the host window path.
2. `SetupGuestGpu(FunctionDispatcher*, KernelState*)` receives guest memory and
   registers the guest GPU MMIO range. `InitializeRingBuffer` supplies the
   live guest ring address and size; the frontend reads it when `CP_RB_WPTR`
   advances.
3. At `PM4_XE_SWAP`, the plugin asks the presenter for its guest output image.
   It passes that presenter's `VkPhysicalDevice`, `VkDevice`, graphics queue,
   queue family, `VkImage`, and `VkImageView` to
   `submit_captured_vulkan_frame`.

The project renderer core takes only those Vulkan handles and draw data. Its
public entry point documents external queue synchronization; it has no
`ANativeWindow`, XCB, Wayland, SDL, or `VkSurfaceKHR` dependency. The Android
and XCB surface adapters remain separate. The core therefore does not need a
new Android host-context callback or a second provider ABI.

## Android ARM64 evidence

The current Process 2 checkout (`699b38a72823b08821b53dc95e45da4d9340f20f`)
configured and built its `native_vulkan` CMake targets for `arm64-v8a`,
`android-29`, with NDK `28.2.13676358`. The `shift_xbox_live_vulkan_renderer`,
`shift_xbox_guest_ring`, `shift_xbox_shader_translate`, and surface-backend
targets compiled. Four resulting checks ran on the connected Redmi Note 8 Pro
(Android API 33, Mali-G76 MC4): PM4 draw input, guest-ring, shader translation,
and synthetic offscreen Vulkan 1.1 draw/readback all exited successfully. The
draw/readback was synthetic and used no validation layer; it did not load the
ReXGlue plugin or run a retail PM4 ring. The checks and binary hashes are
recorded in [`process2_xbox_live_guest_ring_20261023.json`](../evidence/process2_xbox_live_guest_ring_20261023.json).

The reproducible project-core build command is:

```sh
cmake -S native_vulkan -B out/android-vulkan-renderer-arm64 \
  -DCMAKE_TOOLCHAIN_FILE=/home/pes/Android/Sdk/ndk/28.2.13676358/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-29 \
  -DCMAKE_BUILD_TYPE=Release \
  -DVulkan_INCLUDE_DIR=/home/pes/Android/Sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include \
  -DVulkan_LIBRARY=/home/pes/Android/Sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/lib/aarch64-linux-android/29/libvulkan.so
cmake --build out/android-vulkan-renderer-arm64 --parallel 4
```

With the ReXGlue plugin CMake configured for the same NDK/API29 target, the
current `shift_native_gpu_plugin.cpp` translation unit compiled separately
for `aarch64-none-linux-android29` (exit 0; object SHA-256
`9e511eaba290e057d55b4077102a1b45d12164578de67f28beefbef69be3d218`). It
produced one warning from `rex/platform/fpscr.h:78` about the inline-assembly
operand width for `fpcr`. This did not block compiling the renderer-owned
translation unit. The full ReXGlue target was not linked or run on Android.

No Android-only compiler failure was found in the Process 2 parser, shader
translator, live Vulkan renderer, or platform-neutral surface backend. This
does not prove the full ReXGlue Android plugin or Activity build.

## P1 package/runtime requirements

Process 1 owns the Android Activity, runtime, fibers, asset loading, and game
packaging. Its host must:

- package an SDL Android Activity/manifest that keeps SDL's window attached to
  the Android UI lifecycle and exposes its `ANativeWindow` through SDL window
  properties; make its `WindowedAppContext` available for UI-thread calls;
- build and stage `librexgpu-shift-native.so` for `arm64-v8a`, select only
  `shift-native`, and link `rexui-vulkan`, `rexruntime`, and the NDK Vulkan
  loader; the app must not load `rexgpu-xenos`;
- call the existing presentation and guest-GPU setup hooks after the SDL app
  context and guest memory/kernel state exist, then forward resize,
  pause/resume, and native-window replacement through SDL/ReXGlue lifecycle
  handling;
- keep the presenter's Vulkan device, graphics queue, and guest output images
  together. The project renderer cannot consume handles from a second device
  or an unsynchronized queue;
- for a retail output diagnostic, set
  `SHIFT_NATIVE_VULKAN_READBACK_PATH` to an app-private writable path and pull
  the produced image after a guest swap.

P1 reports the current full plugin build is still blocked in its POSIX fiber
backend: Android NDK 28.2's `<ucontext.h>` does not declare
`getcontext`/`makecontext`/`swapcontext`. The affected runtime source is
`src/core/fiber_posix.cpp`; this is outside the Process 2 renderer boundary.
P1 also reports its game target is still `add_executable` with no Android
manifest/Activity package target. I made no changes to those runtime or
packaging files.

## Smallest end-to-end Android verification

After P1 supplies the Android runtime/package path, run the game on the Redmi
with `shift-native`, then require all of the following in one recorded run:

1. The runtime loads `librexgpu-shift-native.so` and does not load
   `rexgpu-xenos`.
2. The plugin reports a guest ring address, consumes a live `CP_RB_WPTR` batch,
   and records at least one supported real draw and one `PM4_XE_SWAP`.
3. The Vulkan presenter reports a submitted frame on the Mali device; the
   app-private readback is pulled and its pixel histogram/hash is recorded.
4. Any unsupported PM4 forms remain reported as skipped; synthetic smoke
   output is never counted as retail visual parity.

The current Linux retail run already proves the live-ring-to-Vulkan submission
contract on a GTX 950 (48 real AutoIndex point draws across two swaps). Its
presenter readback was black, so Android retail output, visible content, and
scene parity remain unverified.
