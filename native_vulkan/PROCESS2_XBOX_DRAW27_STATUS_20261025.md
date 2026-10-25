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

## Current blocker

The Linux run uses the provider branch with the opt-in
`depthStencilResolveSampleZero` contract and proceeds through 24-draw batches
without a renderer refresh failure. The Android APK still contains the older
ReXGlue provider snapshot. On the phone, the initial five-draw loading frame is
read back and displayed; once the game submits 24 draws, refresh fails because
4x-to-1x depth/stencil preservation needs a provider-confirmed enabled resolve
capability. The screen retains the last loading image. The renderer remains
fail-closed when the provider does not advertise that capability.

The separate [ReXGlue provider integration PR #2](https://github.com/Hanz0Hatt0r1/rexglue-sdk/pull/2)
is still the required Android runtime boundary. Building that newer SDK for
Android currently fails in its POSIX fiber implementation because Bionic does
not provide `getcontext`, `makecontext`, and `swapcontext`. Process 2 does not
patch the guest scheduler/runtime or bypass the provider capability contract.

## Verification boundary

- Native Vulkan regressions: 4/4 passed, including Vulkan validation.
- ReXGlue plugin regressions: 3/3 against the current SDK and 4/4 against the
  resolve-capability provider branch.
- ARM64 shader translation regression passed on the Redmi Note 8 Pro. The
  actual frame-10 capture now also exercises the Android retail Vulkan path.
- Android APK signature and both alias library entries were verified; the
  Mali device and 2340x1080 swapchain initialized successfully.
- The actual Android log records eight consecutive 24-draw refresh failures
  after the successful frame-10 readback. This is evidence of the integration
  boundary, not evidence of sustained rendering.

No Process 1 files were changed. Both pre-existing desktop NFS Shift windows
were left open.
