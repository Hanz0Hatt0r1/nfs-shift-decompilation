# Android Vulkan render status (2026-10-24)

## Result

The project-owned Vulkan plugin is **not ready** by the requested on-device
image criterion. It showed the original NFS SHIFT logo once on the Redmi Note 8
Pro, then the foreground game remained black. A captured retail frame with
4x-MSAA followed by two 1x textured draws and Copy/Convert reaches the presenter
without the former sample-count rejection. The logo is visible in the
[on-device screenshot](../../evidence/process2_redmi_note8pro_vulkan_retail_logo_20261024.png).

The logo screenshot was captured at 11:55:12 MSK; a later screenshot at
11:55:24 was black. At 12:04:28 MSK, `NfsShiftActivity` was still foreground
and the screen capture matched the saved black screenshot byte-for-byte. The
runtime reports missing guest assets including `menu_background.xml`. The
first Vulkan readback still records the earlier black startup swap, because
debug readback is captured only once. A transient splash does not satisfy
readiness: an original menu or gameplay image must remain visible through the
Vulkan path. No synthetic image counts as retail parity.


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
11:55:12 MSK, then was black at 11:55:24 MSK and remained byte-identical black
at 12:04:28 MSK. Captured draws and Copy/Convert reached Vulkan without the
mixed-sample refresh failure. Later guest file opens for `audio.bff`,
`drivers2.lod`, `cameraconfig.xml`, and `menu_background.xml` fail; this
coincides with the post-splash black screen, but the log alone does not prove
causation.

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

## Late black-frame diagnostic (2026-10-24)

After a failed incremental APK install removed the test app's external game
directory, the diagnostic APK was installed with a full ADB push and the
3.9-GiB retail game root was restored. The on-device `default.xex` SHA-256
matches the expected retail executable. The fresh run no longer reports a
missing `game_data_root`, but it still shows black output.

The fresh log records 512 Vulkan draw frames, 741 captured draw packets, and
512 Copy/Convert submissions from 12:24:21 to 12:25:55 MSK. At 12:25:55 it
records four failed guest opens for the two `menu_background.xml` paths; no
later draw submission is present in the log. The activity was still foreground
and the screen remained byte-identical black at 12:27:47. The log and condensed
run evidence are in
[`process2_redmi_note8pro_vulkan_late_draw_diagnostic_20261024.json`](../evidence/process2_redmi_note8pro_vulkan_late_draw_diagnostic_20261024.json)
and the compressed raw log
[`process2_redmi_note8pro_vulkan_late_draw_20261024.log.gz`](../evidence/process2_redmi_note8pro_vulkan_late_draw_20261024.log.gz).

The delayed debug sample at 30 seconds captured draws 147–154. All eight use
the same untextured 4x-MSAA three-vertex shader pair and vertex payload. Their
pixel shader writes a zero interpolator. These samples explain black output
for those draws, but they do not establish that every later draw has that
state or prove why the menu scene is absent. Process 1's indexed
[`Menu_Background.bff` archive evidence](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/5b913e2875f095b92a02e13fd393f73148889801/evidence/xbox360_menu_background_pak_index_20261024.json)
finds SGX/ENX and texture members but no `menu_background.xml` member; whether
the loose-file miss is fatal remains unproven.

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
