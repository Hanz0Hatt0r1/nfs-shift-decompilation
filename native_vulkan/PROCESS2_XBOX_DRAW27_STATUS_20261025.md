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

A separate exact-XEX Linux retail run also shows the same disclaimer and purple
strips in its Vulkan window. Its 32-second and 62-second screenshots match by
SHA-256; the disclaimer was present by submit 551. The process mapped plugin
hash `42f338bc…b7f10`, while its command manifest listed the newer handoff hash
`512eb265…278fa98`, so this is evidence for the earlier P2 build, not for the
latest handoff binary. The [Linux frame](../evidence/process2_linux_disclaimer_p1_run021_20261025.png)
and [cross-host evidence record](../evidence/process2_linux_disclaimer_p1_run021_20261025.json)
preserve that discrepancy. The draw/resource source of the strips remains
unisolated.

A later exact-XEX run verifies the current P2 DSO hash `512eb265…278fa98`
against `/proc` and renders a full-screen retail EA intro Bink frame at
presenter frame 551. This confirms the current plugin's Bink path on the GTX
950, not a disclaimer frame or a fix for its purple strips. The Linux provider
also rejected eight earlier 24-draw refreshes because depth/stencil resolve
was not enabled. The same run's 32/40-second X11 captures are black; the last
successful draw submission precedes them, and there is no readback of the last
presenter frame. Current evidence is consistent with the guest ceasing to
submit draws; it does not prove a separate WSI failure. See the [exact-plugin evidence](../evidence/process2_linux_exact_p2_bink_frame551_20261025.json),
[decoded Bink output](../evidence/process2_linux_exact_p2_bink_frame551_20261025.png),
and [raw Vulkan readback](../evidence/process2_linux_exact_p2_bink_frame551_20261025.bin.gz).

The eight mixed-sample refresh rejections were a provider/build mismatch at
source commit `b03c9f87`, not an unsupported shader or a reason to drop depth
contents. In those 24-draw frames, captured 4x and 1x draws both use
depth/stencil on the same target, so the renderer preserves the 4x D24S8
attachment by resolving depth and stencil with `SAMPLE_ZERO` before continuing
at 1x. The old provider API did not request or expose the optional pair
`VK_KHR_create_renderpass2` + `VK_KHR_depth_stencil_resolve` (or Vulkan 1.2 core
promotions), and the plugin therefore passed `false` for the enabled capability.
It correctly failed closed; bypassing the check would lose depth/stencil
semantics.

A resolve-capable Linux x86_64 plugin was built from P2 source `35dab256`
against ReXGlue SDK commit `fb151b94b4956d1c74ba5052e8838b0829eb9c99`. Its
SHA-256 is
`1fa623feecb9a7ac6c1cd8d6de61bcabc6a4a01b12dfbeb9b0255fa29945042c`; the local
artifact is `/home/pes/work/process2-current-p2-resolve-linux-plugin-20261026/librexgpu-shift-native.so`.
The GTX 950/Vulkan 1.4 provider probe reports the resolve pair enabled and
`SAMPLE_ZERO=1` for both aspects. Plugin CTest passed 5/5 and the standalone
native Vulkan CTest passed 4/4 with `VK_LAYER_KHRONOS_validation`, including
depth/stencil preservation and fail-closed regressions. This verifies provider
setup and renderer behavior on the host; the exact retail 24-draw sequence
still needs recapture with this DSO before claiming those frames now render.
Build metadata is in
[`resolve provider build record`](../evidence/process2_linux_resolve_provider_build_20261026.json).

## Resolve-enabled window output transition (2026-10-25)

A P1 exact-XEX run loaded that resolve-capable P2 DSO (`1fa623fe…45042c`) and
recorded 103 successful presenter submissions, each with 14 retail draws. The
last was at 19:29:40.082 MSK; four `menu_background.xml` opens failed 65 ms
later. The window capture at 19:29:47.507 showed the disclaimer text and purple
strips, while the capture at 19:30:02.501 showed only the strips on black. Those
captures were 7.425 and 22.419 seconds after the last submission, respectively.
This establishes a visible window change after guest draw submissions stopped,
but without a paired Vulkan readback it does not identify whether the change is
in the guest output, presenter/WSI lifetime, compositor, or another layer. The
run also emitted A/Start pulses without a same-run retail input-consumer trace,
so their effect is unknown. See the [preserved screenshots, log, and record](../evidence/process2_resolve_blackframe_window_transition_20261025.json).

The next discriminating run should select presenter frame 103 with both
`SHIFT_NATIVE_VULKAN_DUMP_DRAW_FRAME` and
`SHIFT_NATIVE_VULKAN_READBACK_FRAME`, save geometry and texture payloads, and
pair the readback with window captures. This will establish whether frame 103's
Vulkan output still contains the disclaimer when the window becomes strips-only.

A five-sample Android thread snapshot at 18:04:37 shows the guest main thread
at 101% CPU on average, SDL at 87.8%, the two controller threads at 88.8% and
87.2%, while `SHIFT Native GP` stayed at 0%. No later Vulkan submissions
appeared. This points to active guest/runtime work while the renderer worker
was idle, but does not identify the cause. See the [captured thread sample](../evidence/process2_redmi_post_selector_frame1026_threads_20261025.log.gz).

A fresh sample at 18:09:48 shows the same screen and an unchanged screenshot
hash. The guest main thread averaged 98.2% CPU, SDL 84.3%, and the two
controller threads 87.5% and 85.2%; `SHIFT Native GP` remained at 0%. Its
`/proc/.../wchan` was `futex_wait_queue_me`, matching the plugin's wait for the
guest ring to advance at `ring_changed_.wait`; the guest main and controller
threads remained runnable. This supports that no new guest packets were
available for Vulkan submission at that time, but does not identify why the
guest stopped producing them. See the [live thread-state evidence](../evidence/process2_redmi_guest_ring_wait_android_20261025.json)
and [raw sample](../evidence/process2_redmi_guest_ring_wait_threads_20261025.log.gz).

The phone's `PakFiles/Menu_Background.bff` is present and matches both host
retail copies by SHA-256. Its validated Xbox PAK index contains the menu SGX,
ENX, and XTX resources but no `menu_background.xml` member. This narrows the
asset question without establishing an archive fallback or a causal link to
the stopped ring. See the [device archive check](../evidence/process2_redmi_menu_background_archive_presence_20261025.json).

A fresh read-only phone check at 19:18:52 MSK shows the same disclaimer
screenshot and no log writes after the final 14-draw submit at 17:55:35.960.
Over five samples, the guest main thread averaged 94.6% CPU, SDL 81.2%, the two
controller threads 76.7% and 76.9%, and audio 54.8%; `SHIFT Native GP` stayed
at 0%. This confirms that the guest process remains CPU-active while the P2
GPU worker has no new packets. It does not identify why the guest stopped
submitting or connect the nearby XML misses to that stop. See
[`the live recheck record`](../evidence/process2_redmi_disclaimer_idle_recheck_20261025.json).

A follow-up probe at 19:26:31 MSK sent Android `BUTTON_A` and `ENTER`, waiting
three seconds after each. Both resulting screenshots were byte-identical to the
19:18 disclaimer capture; PID 7611 remained alive and its mapped ARM64 renderer
hash was `f84281d8…b9a2f03`, matching the recorded frame-1026 plugin. This
shows no visible response to those inputs, but does not prove the guest received
them or explain the missing submissions. The APK was not reinstalled and the
process was not stopped. The probe is recorded in the same
[`live recheck record`](../evidence/process2_redmi_disclaimer_idle_recheck_20261025.json).

The last logged submission carried 14 draws at 17:55:35.960 MSK. About 0.4
seconds later the guest tried both `D:\tracks\_data\instances\scenes\menu_background.xml`
and `D:\tracks\_data\static\scenes\menu_background.xml`; both returned
`0xc000000f`. No later submission appeared and the activity remained resumed.
The timing does not establish that these file misses caused the stop. The
renderer still has no verified menu-background or race-scene frame, and the
purple strips' draw/resource source remains unknown.

## Current Redmi screen and installed package (2026-10-25)

A read-only ADB capture at 19:48:28 shows the app still resumed as PID 7611.
The 2340x1080 screen has readable safety-disclaimer text and thin purple bars
on black; it does not show the language selector. The installed base APK hash
is `03f76b91…83c4e8df`. Its two packaged ARM64 renderer aliases are byte-identical,
with SHA-256 `f84281d8…b9a2f03` and ELF BuildID
`63b26354123b2e2755d39e89612abf29d0e10777`. This confirms package contents,
but `/proc/7611/maps` is restricted, so the DSO mapped in the running process
was not independently verified in this capture. No APK install or app restart
was performed. See the [device record](../evidence/process2_redmi_current_disclaimer_20261025.json)
and [screen capture](../evidence/process2_redmi_current_disclaimer_20261025.png).

## Verification boundary

- Native Vulkan regressions: 4/4 passed, including Vulkan validation.
- Latest ReXGlue host plugin regressions: 5/5 with
  `VK_LAYER_KHRONOS_validation`, including `EVENT_WRITE_SHD` aliasing, selected
  geometry and RGBA8 texture dumps, readback, and resolve capability. The new
  texture test checks a 1 MiB synthetic white texture fixture; it verifies dump
  plumbing, not retail texture parity. See the [test record](../evidence/process2_selected_draw_dump_regression_20261025.json).
- ARM64 shader translation regression passed on the Redmi Note 8 Pro. The
  actual frame-10 loading capture and later frame-1,026 disclaimer capture
  exercise the Android retail Vulkan path.
- The diagnostic APK signature and renderer DSO hash were verified; its DSO is
  byte-identical to the handed-off production candidate. The Mali device and
  2340x1080 swapchain initialized successfully.
- Host Vulkan and plugin regressions pass with Vulkan validation enabled. The
  phone does not provide `VK_LAYER_KHRONOS_validation`; the live readback is
  runtime evidence, not device validation-layer coverage.

## Current resolve-enabled Android candidate (2026-10-25)

A fresh ARM64 DSO was built from the current P2 source against the resolve SDK
branch and linked with the unchanged runtime DSO extracted from the installed
APK. The generated link passed `--no-undefined`. Both packaged aliases are
identical, and an APK candidate built from the installed base passes zip
alignment and APK v3 signature verification with the same debug signer. It
selects presenter frame 1026 for readback. The candidate has not been installed;
PID 7611 was left untouched. Standalone shell-process probes could not validate
the provider or plugin: the capability check aborted with `std::bad_cast`, and
a minimal `dlopen` probe faulted inside the extracted runtime before returning.
Those failures happened outside the app Activity/JVM context and are
inconclusive about an in-app load. The candidate needs an application-context
retail run before it can be treated as usable. See the [candidate build record](../evidence/process2_current_resolve_android_plugin_candidate_20261025.json).

The retail Linux log also confirms `EVENT_WRITE_SHD` writes the descriptor's
physical base `0x17AF4000` (`1 -> 3 -> 5`), while Vd RPTR writeback separately
updates `0x17AF403C`. A live-ring regression proves the physical store is
visible through guest virtual alias `0xB7AF4000`. This matches ReXGlue's
`EVENT_WRITE_SHD` semantics; it does not explain the retail completion bit or
prove a frontend transition. A same-run P1 probe then confirmed 360 physical
stores were visible through the guest virtual alias and observed the retail
descriptor head advance while RPTR advanced separately. See the [P2 regression evidence](../evidence/process2_event_write_shd_virtual_alias_20261025.json) and
P1's `/home/pes/work/nfs-shift-xbox360-runtime-p1-20261023/evidence/xbox360_linux_guest_ring_physical_virtual_alias_20261025.json`.

This confirms more than the first loading frame, but does not establish
sustained cutscene playback, the complete menu, a race scene, or retail visual
parity.

No Process 1 files were changed. Both pre-existing desktop NFS Shift windows
were left open.
