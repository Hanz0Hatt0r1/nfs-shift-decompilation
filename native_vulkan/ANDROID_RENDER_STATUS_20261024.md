# Android Vulkan render status (2026-10-24)

## Result

The first original retail pixels through the project-owned Vulkan path are now
verified on the Redmi Note 8 Pro: a targeted readback of submitted frame 4
contains 53,098 non-black pixels; the saved and decoded Vulkan image visibly
shows the NFS SHIFT logo, and the device screenshot from the same run shows it
as well. The image is transient; a later screenshot is black.
The first-draw milestone is verified, but the Android game still does not reach
a visible menu or race scene. The earlier logo screenshot is also available
[here](../evidence/process2_redmi_note8pro_vulkan_retail_logo_20261024.png).

The logo screenshot was captured at 11:55:12 MSK; a later screenshot at
11:55:24 was black. At 12:04:28 MSK, `NfsShiftActivity` was still foreground
and the screen capture matched the saved black screenshot byte-for-byte. The
runtime reports missing guest assets including `menu_background.xml`. The
earlier debug build only captured its first black startup swap; later sections
record targeted and late retail-output readbacks. The title splash does not
prove menu, race-scene, or sustained output. No synthetic image counts as
retail parity.


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

## Frame-500 Vulkan output readback (2026-10-24)

The next Android diagnostic build moved its one-shot debug readback to
submitted Vulkan frame 500. It was installed with the same Android signer and
the same retail `default.xex`; the splash screenshot matches the previously
recorded original SHIFT logo. The device run submitted 853 Vulkan frames with
1,416 captured indexed draw packets and 853 accepted Copy/Convert operations.

At 12:41:14.948 MSK, the actual 1280x720 Vulkan guest-output readback at frame
500 contained zero non-black pixels (FNV-1a `68D8B1C5D0E72325`). The phone was
still black on a fresh screenshot at 12:43:07, with the game activity in the
foreground. The guest's four final `menu_background.xml` open failures occur
at 12:42:15.764–.769, after the renderer had continued submitting frames; the
log does not establish whether those failures caused the black scene. The
frame readback, screenshot hashes, APK/plugin hashes, and raw log are recorded
in
[`process2_redmi_note8pro_vulkan_late_readback_20261024.json`](../evidence/process2_redmi_note8pro_vulkan_late_readback_20261024.json)
and
[`process2_redmi_note8pro_vulkan_late_readback_20261024.log.gz`](../evidence/process2_redmi_note8pro_vulkan_late_readback_20261024.log.gz).

This confirms a black Vulkan output in a late retail frame. It narrows the
failure below Android screenshot capture, but does not prove all retail frames
black or identify whether the renderer's supported draw subset, guest scene
resources, or scene progression is responsible. The renderer remains not
ready.

## Exact frame-500 draw follow-up (2026-10-24)

A focused ARM64 diagnostic build logged the guest draw associated with its
frame-500 readback. It was installed with the existing signer and retail XEX;
the game data directory was preserved. The run submitted 521 Vulkan frames,
749 indexed draw packets, and 521 accepted Copy/Convert operations. The
1280x720 readback at 13:10:37.116 MSK again contained zero non-black pixels
(FNV-1a `B161DE6EEC272325`).

The matching captured draw was resolved draw #727: a 4x-MSAA, three-index
auto-indexed rectangle-list draw, with no texture or constants. Its 108-byte
vertex shader forwards vertex attribute 1 to interpolator 0; the three
captured attribute values are all zero. Its 36-byte pixel shader writes
`max(interpolator0, interpolator0)`, so this sampled guest draw evaluates to
zero color. Copy/Convert was accepted immediately afterward. This ties the
black readback to an exact late guest draw and shows that the draw reached the
Vulkan submission path; it does not prove that every frame uses this contract
or identify why the guest has not reached the visible menu/race scene.

Four guest opens for `menu_background.xml` failed about four seconds after the
readback. The temporal order and matching black scene do not establish
causation. A screenshot taken earlier in this run was byte-identical to the
saved post-splash black screenshot. Full draw details, APK/plugin/XEX hashes,
readback metrics, and the compressed runtime log are recorded in
[`process2_redmi_note8pro_vulkan_frame500_draw_20261024.json`](../evidence/process2_redmi_note8pro_vulkan_frame500_draw_20261024.json)
and
[`process2_redmi_note8pro_vulkan_frame500_draw_20261024.log.gz`](../evidence/process2_redmi_note8pro_vulkan_frame500_draw_20261024.log.gz).

## Checks

- Native Vulkan/PM4 suite: 4/4 tests pass (`ctest` in the native Vulkan build).
- Linux AMD64 ReXGlue plugin suite: 3/3 factory, live-ring, and Vulkan readback
  smoke tests pass.
- Rebuilt the Linux AMD64 plugin from the current diagnostic source; the same
  three CTest checks passed 3/3.
- Rebuilt the ARM64 diagnostic plugin with NDK 28.2.13676358 / Android API 29,
  installed and ran it on the Redmi Note 8 Pro, then captured the exact guest
  draw for submitted frame 500. Linux CTest remained 3/3.
- Exact Linux AMD64 diagnostic plugin built from this source: `/home/pes/work/rexglue-sdk-rexui-vulkan-20261023/out/linux-amd64/librexgpu-shift-native.so`, SHA-256
  `e4115b0c58816d9f6225ef102583801fcc7253bf10f52d3e4356e76c8c36a5f0`.
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

## Retail frame-4 readback (2026-10-24)

The Android debug readback frame is configurable with
`SHIFT_NATIVE_VULKAN_DEBUG_READBACK_FRAME`; this run selected frame 4. The
captured batch contains retail draw #4 using the 420-byte vertex shader and
120-byte pixel shader, with the live 1024x256 format-6 texture at guest address
`0x09D57000` (RGBA8 FNV-1a `1FB4AD3D482BE2BB`). No shader override or synthetic
draw was enabled. The completed Vulkan readback reports 53,098 non-black
pixels (FNV-1a `915336228EB84E49`).

A follow-up build set `SHIFT_NATIVE_VULKAN_DEBUG_READBACK_PATH` to save the
actual 3,686,400-byte frame-4 Vulkan readback. Decoding its
`VK_FORMAT_A2B10G10R10_UNORM_PACK32` words yields the
[1280x720 image](../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_decoded_20261024.png)
with the NFS SHIFT title logo; its 53,098 non-black pixels match the runtime
log. The [device screenshot](../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.png)
seven seconds later shows the same logo. A screenshot 55 seconds later is
black while the activity remains foregrounded. This proves the first original
retail output through Vulkan, but does not prove menu, race-scene, or sustained
output. Full draw, raw image, APK/plugin/XEX hashes, decoder details, and run
log are in
[`process2_redmi_note8pro_vulkan_frame4_pixels_20261024.json`](../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.json),
[`process2_redmi_note8pro_vulkan_frame4_pixels_20261024.bin`](../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.bin),
and
[`process2_redmi_note8pro_vulkan_frame4_pixels_20261024.log`](../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.log).

## Xenos cull/front-face state (2026-10-24)

The captured raster contract now requires `PA_SU_SC_MODE_CNTL` (`0x2205`) and
decodes front/back culling plus the `face` winding bit into the Vulkan pipeline.
Cull-front-and-back is rejected. On the Redmi's startup logo batch, live draws
#4/#5 captured `setup=0x218006`: back-face culling enabled and clockwise front
face. Directly forwarding that winding into Vulkan preserves the retail output
with the renderer's captured viewport state. An earlier Y-flip winding
inversion experiment culled the whole retail batch (zero non-black pixels);
the corrected direct mapping restores the prior frame-4 output exactly:
53,098 non-black pixels, FNV-1a `915336228EB84E49`, and byte-for-byte equality
with the existing 3,686,400-byte frame-4 image (`e45a6a3388a12cfcb047d9f94e3120263e219c815cbab59b6e99b0e0f70779e0`).

The updated renderer regression exercises front/back culling and both winding
values under its Y-flipped viewport. Host Vulkan CTest passed 4/4 with
`VK_LAYER_KHRONOS_validation` forced; the ReXGlue plugin suite passed 3/3; and
the isolated Android `arm64-v8a` plugin rebuilt successfully with NDK
28.2.13676358 / API 29. The fixed APK was installed on the Redmi Note 8 Pro
(Mali-G76 MC4, Vulkan 1.1.131), and the on-device frame-4 readback matches the
previous retail logo evidence. The app remained foregrounded after the
post-splash capture, whose black screenshot is byte-identical to the earlier
post-splash screen.

This validates culling on the startup retail draw and does not validate the
menu or race scene. The restored Xbox root still lacks the guest-opened paths
`d:\pakfiles\dir\audio.bff`, `d:\characters\drivers2.lod`,
`d:\tracks\cameraconfig.xml`, and both `menu_background.xml` variants; the
guest logs these failed opens while continuing to submit startup Vulkan draws.
Process 1's read-only cross-check confirms the root is mounted as `D:` and the
retail `default.xex` identity matches; the root contains `PakFiles/*.bff` and
loose UI/audio assets, but not these exact loose paths. The ReXGlue VFS has no
BFF mount/fallback in the inspected SDK, and the indexed
`PakFiles/Menu_Background.bff` contains related `.sgx`/`.enx` resources but no
`menu_background.xml` member. The correct Xbox asset path table/extraction
route remains unresolved; the missing XML alone is not yet proven fatal.
Runtime/VFS ownership remains Process 1. Android validation layers were
unavailable in this app run; validation was exercised on the host. Full raw
log, hashes, root and readback details are recorded in
[`process2_redmi_note8pro_vulkan_cull_state_20261024.json`](../evidence/process2_redmi_note8pro_vulkan_cull_state_20261024.json)
and its [compressed device log](../evidence/process2_redmi_note8pro_vulkan_cull_state_20261024.log.gz).

## Extended live ring follow-up (2026-10-24)

The same installed APK and retail `default.xex` remained foreground on the
Redmi Note 8 Pro. The captured runtime log records 527 successful Vulkan frame
submissions and 527 accepted source-0/sample-0 Copy/Convert operations. The
submissions contain 328 one-draw, 168 two-draw, and 31 three-draw frames, with
no Vulkan refresh failures. The only output readback in this run is frame 4;
its positive title-logo result is documented above.

The eight delayed retail samples (#110–#117) use the same 108-byte VS and
36-byte PS, with an untextured three-index AutoIndex rectangle-list draw.
Captured vertex attribute 1 is zero for all three vertices, and the translated
PS forwards that interpolator, so these sampled draws produce zero color.
The guest later fails to open the `audio.bff`, `drivers2.lod`,
`cameraconfig.xml`, and both `menu_background.xml` paths. The log ends at
those scene-file failures; a fresh screenshot shows the same black screen as
the saved post-splash capture while the activity remains foreground. This
narrows the current failure to the scene/runtime path for this run, but does
not prove the missing files are its only cause. The evidence and full raw log
are in
[`process2_redmi_note8pro_vulkan_live_ring_20261024.json`](../evidence/process2_redmi_note8pro_vulkan_live_ring_20261024.json)
and
[`process2_redmi_note8pro_vulkan_live_ring_20261024.log.gz`](../evidence/process2_redmi_note8pro_vulkan_live_ring_20261024.log.gz).

This is evidence of sustained command submission, not sustained visible
graphics. The native renderer remains incomplete for full menu/race output;
the next renderer implementation must be driven by a non-zero retail scene
draw once the guest reaches and supplies one.


## Loading-frame correction package check (2026-10-24)

The latest Xenos relative-constant, gamma texture/target, and Copy/Convert
channel fixes were built for `arm64-v8a` with NDK 28.2.13676358 / API 29 and
packaged into APK SHA-256
`f2cef95d4dd6d77cdf5f79b56fdb9a62c3f91322bcb847db0e69639d3de2a1df`. The
embedded plugin SHA-256 is
`c01d4006e900edc82c0c733474c6b513e83cd767d06fcc2ea05037cf793d114c`. The APK
was installed with `adb install -r`; the external game directory remained
present.

A launch attempt on the Redmi Note 8 Pro started `NfsShiftActivity`, then
`SDL_main` returned and the activity finished; the launcher became foreground
and no Vulkan frame/readback was produced. Therefore this update has no
on-device visual verification. Earlier Android logo and diagnostic evidence
in this file records earlier APK/plugin builds and remains valid only for
those builds. The current package launch symptom is recorded separately from
the Linux retail frame result.


## Vulkan 1.1 depth/stencil resolve capability (2026-10-24)

A small NDK probe requested Vulkan 1.1 and queried the Redmi Note 8 Pro
(Mali-G76 MC4, API 1.1.131). The physical device advertises both
`VK_KHR_create_renderpass2` and `VK_KHR_depth_stencil_resolve`; its supported
depth and stencil resolve masks are each `0x1`, which is
`VK_RESOLVE_MODE_SAMPLE_ZERO_BIT`. Creating a logical device with both
extensions, retrieving `vkCreateRenderPass2KHR`, and creating the D24S8 4x to
1x sample-zero resolve render pass all returned `VK_SUCCESS`.

The current ARM64 renderer regression binary then ran offscreen on that phone
and passed the 4x-to-1x depth/stencil preservation checks. That regression
uses synthetic smoke draws and establishes Vulkan driver behavior only, not
retail parity. On the host, the full renderer suite passed 4/4 and the ReXGlue
plugin suite passed 3/3 with `VK_LAYER_KHRONOS_validation`; Android validation
was not active. The result and hashes are recorded in
[`process2_redmi_note8pro_depth_resolve_20261024.json`](../../evidence/process2_redmi_note8pro_depth_resolve_20261024.json).

The live plugin obtains a `VkDevice` from ReXGlue's Vulkan provider, so it
cannot enable device extensions after creation. Process 1 accepted the
backward-compatible optional capability contract: request both resolve
extensions atomically when supported (including Vulkan 1.2 core promotion),
report the enabled capability to the plugin, and leave unrelated GPU-emulation
feature requests disabled. Provider wiring is pending in Process 1. Until then
the current plugin passes `false` explicitly and rejects a mixed 4x-to-1x
depth/stencil frame before submission. A subsequent retail frame is still
required to establish whether Xenos uses the same sample-zero rule and to
verify menu/gameplay output.
