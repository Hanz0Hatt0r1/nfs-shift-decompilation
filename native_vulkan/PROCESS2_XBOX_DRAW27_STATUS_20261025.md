# Process 2 retail Vulkan frontier — 2026-10-25

The current Linux retail run now produces and reads back the real SHIFT loading
screen through the project-owned Vulkan live-ring renderer. The Redmi Note 8 Pro
also produced a matching retail Vulkan readback with no synthetic fragment
override. Both captures show the complete `Loading...` text and the confirmed
yellow-orange filled / dark-gray empty progress bar.

## Retail evidence

- Linux on the GTX 950 accepted 97 Copy/Convert operations and submitted 739
  captured indexed draw packets, including 19 batches of 24 draws, with no
  renderer refresh failures. Frame 10 contains 59,101 non-black pixels
  (`26C9600EEF8AB16F`). The run later reports its swapchain surface outdated.
  The first logged unresolved draw is #0, missing captured raster registers
  (`valid_mask=0x17038`). See the [decoded frame](../evidence/process2_linux_retail_loading_frame10_20261025.png),
  [raw readback](../evidence/process2_linux_retail_loading_frame10_20261025.bin),
  [run metadata](../evidence/process2_linux_retail_loading_frame10_20261025.json),
  and [compressed log](../evidence/process2_linux_retail_loading_frame10_20261025.log.gz).
- On the Redmi Note 8 Pro (Mali-G76, Vulkan 1.1.131), frame 10 contains
  59,103 non-black pixels (`0FED7AEE9AE4656E`) and matches the device
  screenshot. The retail data root was copied in full; `default.xex` and
  `BOOTSPLASH.bff` hashes match the host copies. See the [device screenshot](../evidence/process2_redmi_note8pro_vulkan_frame10_pixels_20261025.png),
  [decoded Vulkan readback](../evidence/process2_redmi_note8pro_vulkan_frame10_pixels_20261025_decoded.png),
  [raw readback](../evidence/process2_redmi_note8pro_vulkan_frame10_pixels_20261025.bin),
  [run metadata](../evidence/process2_redmi_note8pro_vulkan_frame10_pixels_20261025.json),
  and [full runtime log](../evidence/process2_redmi_note8pro_vulkan_frame10_pixels_20261025.log).

These are actual retail loading-screen pixels from the translated guest draw
path, not a synthetic Vulkan scene. They do not establish menu, race, or full
retail visual parity.

## Current Android state

The earlier Android depth/stencil-resolve provider failure is superseded by a
later APK built with the resolve-capable provider. On the Redmi Note 8 Pro, the
live run reached 1,182 successful Vulkan submissions (10,471 captured draw
packets) and accepted 1,182 Copy/Convert operations, with no presenter refresh
failures. A separate live selector capture shows all six language labels
readable on the device; it supersedes the earlier missing-label observation.
The heading, select prompt, and dimmer non-selected rows are visible in the
[Redmi selector screenshot](../evidence/process2_redmi_language_selector_live_android_20261025.png).

At submitted frame 1,026, an actual Vulkan output readback contains 17,951
non-black pixels (`AA8BC55196A29A73`). After scaling the centered 16:9 Android
viewport to the readback extent, the decoded image closely matches the
contemporaneous device screenshot. The screenshot and readback both show the
original safety disclaimer and thin purple strips. See the [readback metadata](../evidence/process2_redmi_post_selector_frame1026_20261025.json),
[decoded Vulkan output](../evidence/process2_redmi_post_selector_frame1026_readback_decoded_20261025.png),
[raw Vulkan output](../evidence/process2_redmi_post_selector_frame1026_readback_20261025.bin),
[device screenshot](../evidence/process2_redmi_post_selector_frame1026_device_20261025.png),
and [compressed runtime log](../evidence/process2_redmi_post_selector_frame1026_runtime_20261025.log.gz).

A five-sample Android thread snapshot at 18:04:37 shows the guest main thread
at 101% CPU on average, SDL at 87.8%, the two controller threads at 88.8% and
87.2%, while `SHIFT Native GP` stayed at 0%. No later Vulkan submissions
appeared. This points to active guest/runtime work while the renderer worker
was idle, but does not identify the cause. See the [captured thread sample](../evidence/process2_redmi_post_selector_frame1026_threads_20261025.log.gz).

The last logged submission carried 14 draws at 17:55:35.960 MSK. About 0.4
seconds later the guest tried both `D:\tracks\_data\instances\scenes\menu_background.xml`
and `D:\tracks\_data\static\scenes\menu_background.xml`; both returned
`0xc000000f`. No later submission appeared and the activity remained resumed.
The timing does not establish that these file misses caused the stop. The
renderer still has no verified menu-background or race-scene frame, and the
purple strips' draw/resource source remains unknown.

## Verification boundary

- Native Vulkan regressions: 4/4 passed, including Vulkan validation.
- ReXGlue plugin regressions: 3/3 against the current SDK and 4/4 against the
  resolve-capability provider branch.
- ARM64 shader translation regression passed on the Redmi Note 8 Pro. The
  actual frame-10 loading capture and later frame-1,026 disclaimer capture
  exercise the Android retail Vulkan path.
- The diagnostic APK signature and renderer DSO hash were verified; its DSO is
  byte-identical to the handed-off production candidate. The Mali device and
  2340x1080 swapchain initialized successfully.
- Host Vulkan and plugin regressions pass with Vulkan validation enabled. The
  phone does not provide `VK_LAYER_KHRONOS_validation`; the live readback is
  runtime evidence, not device validation-layer coverage.

This confirms more than the first loading frame, but does not establish
sustained cutscene playback, the complete menu, a race scene, or retail visual
parity.

No Process 1 files were changed. Both pre-existing desktop NFS Shift windows
were left open.
