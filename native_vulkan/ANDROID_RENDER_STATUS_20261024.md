# Android Vulkan render status (2026-10-24)

## Result

The project-owned Vulkan plugin now displays the original NFS SHIFT logo on the
Redmi Note 8 Pro. A captured retail frame with 4x-MSAA followed by two 1x
textured draws and Copy/Convert reaches the presenter without the former
sample-count rejection. The logo is visible in the [on-device screenshot](../../evidence/process2_redmi_note8pro_vulkan_retail_logo_20261024.png).

The renderer is not ready for the full game: a later screenshot from the same
run is black, and the runtime reports missing guest assets including
`menu_background.xml`. The first Vulkan readback still records the earlier
black startup swap, because debug readback is captured only once. The later
screenshot and successful frame submissions establish the retail logo output;
they do not establish menu, race-scene, or full-game parity. No synthetic image
is counted as retail parity.


## Hardware and input

- Device: Redmi Note 8 Pro (`begonia`), Android API 33.
- GPU: ARM Mali-G76 MC4; Vulkan API 1.1.131.
- Input: retail Xbox `default.xex`, SHA-256
  `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`.
- Renderer path: emulator-free ReXGlue Vulkan plugin, PM4 guest ring to native
  Vulkan submission.

## Evidence

The earlier black-only run below is historical. The fresh follow-up records
both the visible splash logo and the later black state in
[`process2_redmi_note8pro_vulkan_retail_logo_20261024.json`](../../evidence/process2_redmi_note8pro_vulkan_retail_logo_20261024.json).

Fresh APK/plugin hashes: APK `0da8ef30127bdc5269a91f2fdf3dd0ade8ffd1b135014df07d466dde428f815d`,
ARM64 plugin `2aa5194728eb916ac80ab109253ed671f74913191f8eac6e869e8da22176b2c9`.
The first mixed retail frame contains sample counts `[4, 1, 1]`; the 1024x256
texture at guest address `0x09D57000` normalizes to RGBA8 FNV-1a
`1FB4AD3D482BE2BB`. The Android screenshot displayed the NFS SHIFT logo at
11:55:12 MSK, then was black at 11:55:24 MSK. The log has repeated successful
three-draw Vulkan submissions and no mixed-sample refresh failure. Later guest
file opens for `audio.bff`, `drivers2.lod`, `cameraconfig.xml`, and
`menu_background.xml` fail; this coincides with the post-splash black screen,
but the log alone does not prove causation.

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
- Host Vulkan renderer regression: passes with
  `VK_LAYER_KHRONOS_validation` on NVIDIA GeForce GTX 950 with no validation
  errors; it covers synthetic test draws and mixed-sample Copy/Convert.
- Device result: original splash logo displayed through Vulkan; later menu and
  gameplay output remain unverified.

Next renderer work is to capture and implement the actual menu/race draw
contracts when the guest supplies those resources. The observed missing guest
asset paths are a Process 1 runtime boundary; the current screenshot and log
are recorded separately so a later visible-scene claim can be verified.

## Android ARM64 build boundary (2026-10-24)

The earlier standalone build boundary is superseded by the 2026-10-24 isolated
ARM64 build: `rexgpu-shift-native` compiled with NDK 28.2.13676358 for
`arm64-v8a` / Android API 29, with Tracy/perf counters disabled to match the
existing APK. That plugin was packaged under both Android loader names and
loaded by the existing debug app. It displayed the retail splash logo on the
Redmi Note 8 Pro. This does not verify later menu or race-scene output.
