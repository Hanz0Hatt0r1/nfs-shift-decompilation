# Process 2 — Xbox 360 SHIFT frame-4 Vulkan readback

**Date:** 2026-10-24 (MSK)

**Result:** The saved frame-4 Vulkan guest-output image contains the original
SHIFT title logo and matches the device screenshot from the same run. The logo
was transient: a later screenshot was black, and the game remains black in a
fresh foreground-device check. This proves the first original retail output,
not a sustained menu/race renderer.

## Capture and device

- Device: Redmi Note 8 Pro (`begonia`), Android API 33, Mali-G76 MC4, Vulkan
  1.1.131; package `com.hanz0hatt0r.nfsshift`.
- Capture run: 2026-10-24 15:05:48–15:06:54 MSK. The debug build selected
  submitted Vulkan frame 4 and wrote the raw image to the app's private files.
- Retail Xbox 360 `default.xex` SHA-256 before and after install:
  `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`.
- ARM64 plugin SHA-256:
  `1c63f916a1d898837445f59c8de040bea29b18616ce4bf861f66719f0639af20`.

The frame-4 batch submitted three captured indexed retail draws. Resolved draw
#4 uses the captured 1024x256 format-6 texture at guest address `0x09D57000`
(normalized RGBA8 FNV-1a `1FB4AD3D482BE2BB`) with the original 420-byte vertex
shader (`D8675FD6D20F2BD6`) and 120-byte pixel shader
(`2925CC56719921EB`). The captured Copy/Convert was accepted. No synthetic
fragment override was enabled.

## Readback verification

The existing raw Vulkan readback was present, so no new frame-4 device capture
was needed:

- Extent/format: 1280x720, `VK_FORMAT_A2B10G10R10_UNORM_PACK32`.
- Raw size: 3,686,400 bytes; SHA-256
  `e45a6a3388a12cfcb047d9f94e3120263e219c815cbab59b6e99b0e0f70779e0`.
- Recomputed FNV-1a 64-bit over raw bytes:
  `915336228EB84E49`, matching the runtime log.
- Recomputed non-black RGB pixel count: 53,098, matching the runtime log.
- Decoded PNG: 1280x720; SHA-256
  `e53eab4da44b69672b136b56d98978598aa018a9e786aa5a8e72e351545e6683`;
  decoded non-black count is also 53,098.

The packed 10:10:10:2 UNORM words were read as little-endian 32-bit values;
R/G/B are bits 0–9, 10–19, and 20–29, scaled to 8-bit channels. The resulting
image visibly contains the NFS SHIFT title logo. The phone screenshot at
15:05:59.988, about seven seconds after the readback, shows the same logo.

At 15:06:54.371 the phone screenshot was black while `NfsShiftActivity`
remained foregrounded; Vulkan submissions continued in the log. A fresh ADB
check at 15:13:02 again found that activity foregrounded and the screen black.
Its screenshot SHA-256 (`2f7c5a4966a5d8fe95be1f9e18c4735565e3c5a82657b50bda971758efdaf839`)
matches the saved post-splash black screenshot byte-for-byte.

## What this establishes

- Original retail texture/shader input reached the project-owned Vulkan path.
- The actual Vulkan guest-output readback contains the original title-logo
  pixels, and the device displayed that image during the same run.
- The first visible retail draw is verified on Redmi Note 8 Pro.

It does **not** establish sustained output, a visible menu, a race scene, or
full retail parity. The later black screen is real, but this capture does not
identify its cause. Guest file-open failures for `audio.bff`, `drivers2.lod`,
and `cameraconfig.xml` occur later in the log; their relationship to the black
screen is not proven. A separate frame-500 diagnostic also records black Vulkan
output for one later draw whose captured interpolator values are zero; that
sample does not characterize every later draw.

## Evidence

- [Machine-readable run record](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.json)
- [Raw Vulkan frame](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.bin)
- [Decoded Vulkan image](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_decoded_20261024.png)
- [Device screenshot after readback](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.png)
- [Later black screenshot](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_later_20261024.png)
- [Saved post-splash black screenshot matching the fresh ADB check](../../evidence/process2_redmi_note8pro_vulkan_post_splash_black_20261024.png)
- [Full device log](../../evidence/process2_redmi_note8pro_vulkan_frame4_pixels_20261024.log)
- [Frame-500 draw diagnostic](../../evidence/process2_redmi_note8pro_vulkan_frame500_draw_20261024.json)
- [Android renderer status and earlier diagnostics](../../native_vulkan/ANDROID_RENDER_STATUS_20261024.md)

No Process 1 runtime files were changed for this report.
