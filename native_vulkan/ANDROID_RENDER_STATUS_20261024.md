# Android Vulkan render status (2026-10-24)

## Result

The renderer is not ready to show the retail game. On Redmi Note 8 Pro, the
Vulkan 1.1 provider and Android swapchain initialize, and the guest PM4 ring
reaches the native presenter. A captured indexed draw is submitted, but the
captured Vulkan output is entirely black. Later batches with three captured
draws are rejected because their target/scissor state differs from
`PM4_XE_SWAP`.

No synthetic image is counted as retail parity.

## Hardware and input

- Device: Redmi Note 8 Pro (`begonia`), Android API 33.
- GPU: ARM Mali-G76 MC4; Vulkan API 1.1.131.
- Input: retail Xbox `default.xex`, SHA-256
  `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`.
- Renderer path: emulator-free ReXGlue Vulkan plugin, PM4 guest ring to native
  Vulkan submission.

## Evidence

Raw device log: `/tmp/process2-redmi-note8pro-event-write-20261024.log`,
SHA-256 `650f49e356d39144633faa8638402c27aa0b969035b10d194972acd9b203a43b`.

Screenshot: `/tmp/process2-redmi-note8pro-event-write-20261024.png`, SHA-256
`2f7c5a4966a5d8fe95be1f9e18c4735565e3c5a82657b50bda971758efdaf839`.

Key log evidence:

- Lines 6 and 57–64: Mali Vulkan 1.1 device and Android swapchains initialize.
- Lines 73–74: captured `EVENT_WRITE_SHD` packets update guest descriptor
  `0x17AF4000` and companion dword `0x17AF4004`.
- Line 84: one captured indexed draw reaches the Vulkan presenter.
- Line 85: Android debug readback reports zero non-black pixels and FNV-1a
  `B161DE6EEC272325`.
- Lines 111 onward: three-draw batches fail the captured target/scissor check.
- Lines 101–106: guest requests relative `render\\shaders` without a VFS
  device; this is an outstanding runtime compatibility issue tracked with
  Process 1.

The source regression test now decodes captured `EVENT_WRITE_SHD` address,
Xenos endian mode, packet value, and swap-counter initiator semantics. It
applies writes through ReXGlue's guest-memory helpers, matching the SDK's
`GpuSwap` behavior. This advances guest synchronization; it does not make the
rendered frame correct.

## Checks

- Native Vulkan/PM4 suite: 4/4 tests pass (`ctest` in the native Vulkan build).
- Linux AMD64 ReXGlue plugin suite: 3/3 factory, live-ring, and Vulkan readback
  smoke tests pass.
- Exact Linux AMD64 plugin built from this source: `/home/pes/work/rexglue-sdk-rexui-vulkan-20261023/out/linux-amd64/librexgpu-shift-native.so`, SHA-256
  `c425619827add26839f3f111cc069c63141434eb89feb5e3abc97a0a36e9182a`.
- Device Vulkan validation: swapchain creation and draw submission observed;
  rendered image is black, so visual parity fails.

Next critical work is to capture the retail guest-memory transition under the
Linux Process 1 runtime, then resolve the actual draw's render-target/scissor,
shader, and resource state from captured PM4 rather than inventing a frame.

## Android ARM64 build boundary (2026-10-24)

The `shift_xbox_live_vulkan_renderer` static target compiles with NDK
28.2.13676358 for `arm64-v8a` / Android API 29. The resulting archive is
`/home/pes/work/process2-p2161-plugin-android-build/libshift_xbox_live_vulkan_renderer.a`
(SHA-256 `60495be0e7887ca31b19dbd4796d951ba14059acc8601d0ae12e0e895a8011bd`).

The full `rexgpu-shift-native` target still fails while compiling the external
ReXGlue SDK's `src/core/fiber_posix.cpp`: Android NDK Clang does not declare
`getcontext`, `makecontext`, or `swapcontext`. P2 did not modify SDK/runtime
files. This verifies ARM64 compilation of the renderer library, not a packaged
Android plugin or APK integration; the on-device black-output evidence above
remains the only retail-device result.
