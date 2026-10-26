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
renderer still has no verified menu-background or race-scene frame. A later
targeted disclaimer capture isolated the purple strips to four real draws and
one sampled texture; it did not establish whether those pixels are expected.

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

The candidate described in the [build record](../evidence/process2_current_resolve_android_plugin_candidate_20261025.json)
was subsequently installed with ADB incremental install (the regular replace
failed for insufficient storage), preserving app data. The installed APK hash
and the mapped ARM64 plugin were verified in the app process. On the Redmi Note
8 Pro it displayed Loading, the EA intro, and the legal disclaimer; its frame
1026 Vulkan readback matches the screen capture after accounting for the
device-to-readback scaling. The run left the app open on the disclaimer. This
supersedes the earlier “not installed” status for that exact candidate; the
prior standalone shell probes remain inconclusive because they ran outside the
app Activity/JVM context. See the [live startup record](../evidence/process2_redmi_resolve_candidate_live_startup_20261025.json)
and its [Loading](../evidence/process2_redmi_resolve_candidate_loading_20261025.png),
[EA intro](../evidence/process2_redmi_resolve_candidate_ea_intro_20261025.png),
[disclaimer](../evidence/process2_redmi_resolve_candidate_disclaimer_20261025.png),
and [decoded frame 1026](../evidence/process2_redmi_resolve_candidate_frame1026_readback_decoded_20261025.png).

The language selector did not appear in this run because the earlier English
choice remained in preserved app data. The earlier device capture established
that its labels were readable. Thin purple bars still show on the disclaimer;
the menu after the disclaimer, race scenes, and sustained cutscene playback are
not yet verified. The GPU worker later waited in `futex_wait_queue_me`, which is
consistent with the renderer waiting for more ring packets but does not prove
why the guest stopped submitting them.

The retail Linux log also confirms `EVENT_WRITE_SHD` writes the descriptor's
physical base `0x17AF4000` (`1 -> 3 -> 5`), while Vd RPTR writeback separately
updates `0x17AF403C`. A live-ring regression proves the physical store is
visible through guest virtual alias `0xB7AF4000`. This matches ReXGlue's
`EVENT_WRITE_SHD` semantics; it does not explain the retail completion bit or
prove a frontend transition. A same-run P1 probe then confirmed 360 physical
stores were visible through the guest virtual alias and observed the retail
descriptor head advance while RPTR advanced separately. See the [P2 regression evidence](../evidence/process2_event_write_shd_virtual_alias_20261025.json) and
P1's `/home/pes/work/nfs-shift-xbox360-runtime-p1-20261023/evidence/xbox360_linux_guest_ring_physical_virtual_alias_20261025.json`.

These host and device observations do not establish sustained cutscene
playback, the complete menu, a race scene, or retail visual parity.

No Process 1 files were changed. Both pre-existing desktop NFS Shift windows
were left open.

## Disclaimer strip draw isolation (2026-10-26)

A fresh exact-XEX Linux replay using the Process 2 pipeline-cache plugin captured
submit 907 with readback and per-draw geometry/texture dumps. Four draws
(#5058-#5061) form the upper and lower left/right strips. All four sample the
same 512x8 Xenos format-20 (`DXT4/5`) texture at guest address `0x0A24B000`;
the renderer's normalized RGBA8 bytes match across the four draws. Their
captured vertex bounds align with the visible strip segments. The
[decoded Vulkan frame](../evidence/process2_linux_disclaimer_frame907_readback_20261026.png)
shows the original safety text and the same four strips, while the
[draw-level evidence record](../evidence/process2_disclaimer_draw_isolation_20261026.json)
preserves the exact host, runtime, XEX, plugin, readback, geometry, texture,
and shader hashes.

A read-only Redmi Note 8 Pro capture taken on 2026-10-26 also shows the same
disclaimer and strips. After cropping its centered 16:9 viewport and bilinear
scaling to the Linux readback, 893,861 of 921,600 RGB pixels match exactly;
mean absolute channel difference is 0.379. The phone's mapped DSO could not be
verified because Android denied access to `/proc/24808/maps`, so this is a
same-screen comparison, not proof that the identical plugin binary produced
both outputs or that they match an independent Xenos render.

The strips' draw and texture source is now isolated, but their expectedness is
not. No texture or blend-state change was made without an independent retail
reference. The selector-label issue is separately verified: the live Redmi
selector capture shows all six labels after the interpolator-location shader
fix. Gameplay, post-disclaimer menu rendering, and sustained cutscene playback
remain unverified. The phone app was left resumed, and no Process 1 source was
changed.

## Redmi retail Bink pipeline-cache replay (2026-10-26)

The latest renderer core was replayed on the Mali-G76 with the captured retail
Bink draw #2614 and the same three R8 planes used by the earlier async-in-flight
measurement. Across three alternating runs, the pipeline-cache build produced
byte-identical readback and used 36% less replay-thread CPU time on average
(1.303 ms vs. 2.043 ms per call). Wall time averaged 8.123 ms vs. 7.887 ms and
did not improve in this sample. This isolates one GPU submission call; it does
not measure Bink decode, the full mixed-sample frame, game scheduling, or
end-to-end cutscene speed. The
[A/B record](../evidence/process2_redmi_bink_pipeline_cache_20261026.json)
includes the old/current replay hashes, shader/plane hashes, all samples, and
the unchanged live-app state. The game remained resumed and was not reinstalled
or restarted.

## Redmi retail Bink sampler-cache replay (2026-10-25)

The ARM64 Release renderer now reuses matching `VkSampler` objects in a
64-entry per-device cache. Cache clearing waits for in-flight frames before
destroying samplers. The native regression checks same-state reuse, distinct
filter-state separation, cached/uncached image equality, and safe clear after
asynchronous submissions.

Three alternating Mali-G76 pairs replayed the actual retail Bink draw #2614.
Readback SHA-256 matched baseline byte-for-byte (`8295d56a…55f41ca1`). Mean
wall times were 7.950 ms vs. 8.000 ms and replay-thread CPU was 1.427 ms vs.
1.466 ms; this does not establish a material speedup. Native Vulkan and plugin
CTest each pass 4/4 with `VK_LAYER_KHRONOS_validation`; the ARM64 Release core
build and replay also pass. Android has no validation layer. The game remained
resumed, its before/after screenshot hash was unchanged, and no APK, input, or
restart was used. One offscreen draw does not establish full cutscene or game
performance. See the [A/B record](../evidence/process2_redmi_bink_sampler_cache_20261025.json)
and [matching raw readback](../evidence/process2_redmi_bink_sampler_cache_frame2614_20261025.bin.gz).

## Redmi Bink source-frame comparison (2026-10-26)

I rebuilt the ARM64 renderer archive from current source `e908a6829` and
replayed the captured retail Bink draw on the Mali-G76. The current build
produced the same 1280x720 A2B10G10R10 readback SHA as the prior capture
(`8295d56a…55f41ca1`); the final readback after eight asynchronous replays
matched the first. The live game process stayed resumed at the disclaimer; the
replay sent no game input and did not install or restart the app.

For an independent content check, I decoded all 281 frames of the retail
`Franchise_Ident.bik` with FFmpeg and compared them with the Vulkan image. The
closest 160x90 RGB match is frame 244 (MAE 0.178). At full resolution, 839,930
of 921,600 RGB pixels match exactly; per-channel MAE is 0.159/0.134/0.165.
This confirms that the captured shader and Y/V/U planes produce the original
EA intro content on the current renderer build. It is one captured-draw replay,
not evidence of sustained live cutscene playback or a complete game scene.
Raw movie and plane bytes were not added to the repo. See the
[Bink frame comparison record](../evidence/process2_redmi_bink_frame244_reference_20261026.json).

## Redmi retail Bink sequence replay (2026-10-25)

To check frame-to-frame texture updates, I decoded the original 281-frame
`Franchise_Ident.bik` with FFmpeg and submitted every YUV420 frame through the
captured retail Bink draw #2614 and its Vulkan 1.1 shaders on the Redmi Mali-G76.
The renderer reused its R8 upload/image cache while replacing all three video
planes before each draw. All 281 submissions completed; mean submit time was
1.684 ms, p95 was 3.238 ms, and mean submit-thread CPU time was 1.207 ms.

Readbacks for frames 0, 140, and 280 were compared against independent FFmpeg
decodes. Frames 0 and 280 produced identical renderer PNGs and each differed
from the source by at most one RGB level. Frame 140 had per-channel MAE
1.723/0.454/2.100 and max difference 19/6/38. The [stream evidence](../evidence/process2_redmi_bink_stream_replay_20261025.json)
records hashes, timings, and limitations; [frame 0](../evidence/process2_redmi_bink_stream_frame000_20261025.png)
and [frame 140](../evidence/process2_redmi_bink_stream_frame140_20261025.png)
are decoded Vulkan readbacks. The existing renderer regression also verifies
that changing an R8 video plane updates cached output and matches an uncached
render.

This is an offscreen renderer replay using FFmpeg-decoded frames from the retail
movie. It verifies repeated plane uploads and captured-draw submissions on the
device; it does not exercise the guest Bink decoder, the live presenter, or the
game's cutscene scheduling. The app stayed resumed at the disclaimer; its
before/after screenshot hashes match, and no input, reinstall, or restart was
used. Android has no Vulkan validation layer, so validation coverage remains
from host CTest. No Process 1 files were changed.

## Redmi current runtime frontier (2026-10-26)

A read-only check of the currently installed app found it still resumed as PID
24808 on the Redmi Note 8 Pro. Its latest retained guest log records 1,090
accepted source-0/sample-0 Copy/Convert operations and 1,090 successful Vulkan
presenter submissions between 20:36:46 and 20:38:20 MSK. The only unresolved
draw reason logged was draw #0's incomplete raster state (`valid_mask=0x17038`).
The runtime then logged two failed opens for `D:\tracks\_data\instances\scenes\menu_background.xml`
and `D:\tracks\_data\static\scenes\menu_background.xml` at 20:38:21. The
screen captured at 00:08:18 MSK remains the legal disclaimer with the same
purple strips; its SHA-256 matches the earlier capture. The app was not
restarted and no input was sent. See the [device record](../evidence/process2_redmi_menu_scene_block_20261026.json),
[screen capture](../evidence/process2_redmi_menu_scene_block_20261026.png), and
[compressed guest log](../evidence/process2_redmi_menu_scene_block_20261026.log.gz).

This confirms that the live session currently provides no post-disclaimer menu
or race draws to specify another renderer change. The file failures are owned
by Process 1's runtime/content path; their timing does not prove causality. The
observed 1280x720 Copy/Convert path is exercised live, but this does not prove
other EDRAM resolve forms or full retail parity. The Android process map is
restricted, so the loaded renderer DSO hash is unknown. No Process 1 files were
changed.

## Latest Android selector verification (2026-10-26)

The latest P2 candidate was installed on the Redmi Note 8 Pro with incremental
ADB install. Its language-selector screenshot clearly shows the heading,
selection prompt, and all six labels. After one A-button event, the game
rendered its original NFS SHIFT title sequence and reached the legal
disclaimer. All six language labels are visible in the current Android
candidate's live retail selector capture; the earlier missing-label symptom
is fixed.

The guest log contains 1,233 presenter submissions with 11,267 captured
indexed packets and 1,233 accepted Copy/Convert operations; no presenter
refresh failures were reported. Draw #0 still fails closed with incomplete
raster state (`0x17038`). `menu_background.xml` lookups fail shortly after the
last submissions, but the timing does not show causality. The app was left
open. Evidence and hashes are in
[`the latest Android selector record`](../evidence/process2_redmi_language_selector_latest_android_20261026.json),
[selector screenshot](../evidence/process2_redmi_language_selector_latest_android_20261026.png),
[title screenshot](../evidence/process2_redmi_language_selector_title_latest_android_20261026.png),
and [compressed guest log](../evidence/process2_redmi_language_selector_latest_android_20261026.log.gz).

A read-only ADB recheck later confirmed PID 17268 remained top-resumed on the
legal disclaimer. Process 2 sent no further input and did not stop the app;
the [current screen](../evidence/process2_redmi_language_selector_latest_current_screen_20261026.png)
and status are recorded in the same evidence JSON.

This candidate packages the current P2 ARM64 plugin against the unchanged
Android runtime DSO because the SDK's full application target still fails in
its POSIX fiber source on Bionic's missing `getcontext`, `makecontext`, and
`swapcontext`. The live launch verifies that plugin/runtime combination, not
a full runtime rebuild. Android Vulkan validation-layer coverage is
unavailable. The post-disclaimer menu, racing scenes, and complete retail
parity remain unverified.

## Latest renderer handoff for Process 1 (2026-10-26)

Built the current P2 source as an x86_64 plugin against the resolve-capable
ReXGlue SDK already used by Process 1. The plugin and its matching
`librexruntime.so` are staged together at
`/home/pes/work/process2-latest-renderer-handover-20261026/linux-amd64/`.
Plugin CTests pass 5/5 and native Vulkan CTests pass 4/4 with
`VK_LAYER_KHRONOS_validation` forced through the loader. The native shader
regression covers preservation of nonzero interpolator locations, including
the location needed by the language font shader. This does not replace a fresh
P1 retail run with this exact Linux build.

The matching Android candidate is installed on the Redmi Note 8 Pro; the
installed APK hash matches the packaged file. All six language labels are
visible, the original title sequence rendered, and the app remains resumed on
the disclaimer. APK, plugin/runtime hashes, test commands, screenshots, and
limits are recorded in
[`the handoff evidence`](../evidence/process2_latest_renderer_handoff_20261026.json).

## Redmi post-disclaimer input probe (2026-10-26)

The currently resumed Redmi app was left on the legal disclaimer. I sent one
`KEYCODE_BUTTON_A` and captured the screen ten seconds later. The before/after
screenshots have the same SHA-256, PID 15722 remained top-resumed, and the guest
log snapshot is byte-identical to the pre-input snapshot. Its last renderer
batch remains at 11:52:06.902, followed by four failed `menu_background.xml`
opens; the final warning is at 11:52:07.332. No new renderer draw contract was
observed. The event's delivery to the guest is unconfirmed, and the nearby file
failures do not establish why progression stopped. The app was not restarted
or closed. See the [probe record](../evidence/process2_redmi_disclaimer_after_a_20261026.json)
and [post-input screenshot](../evidence/process2_redmi_disclaimer_after_a_20261026.png).

## PM4 interrupt ordering candidate on Redmi (2026-10-26)

Installed the latest P2 Android plugin against the byte-identical packaged
runtime without clearing application data. The screen showed the original
Loading text/progress bar at 15 seconds, then the original safety disclaimer
at 40 seconds. English was already saved, so this launch did not show the
language selector. The immediately preceding Redmi candidate capture contains
the heading and all six language names; the current source preserves its
interpolator-location fix. A later recheck found PID 21346 alive and NFS back
in the foreground on a black screen; no app stop was issued. A key event was
sent only after a screenshot showed another package foregrounded, so it is not
counted as an NFS test; its effect is unknown.

See the [candidate evidence](../evidence/process2_pm4_interrupt_order_android_smoke_20261026.json),
[Loading capture](../evidence/process2_redmi_pm4_interrupt_order_loading_20261026.png),
and [disclaimer capture](../evidence/process2_redmi_pm4_interrupt_order_disclaimer_20261026.png),
plus the [later black-screen recheck](../evidence/process2_redmi_pm4_interrupt_order_black_recheck_20261026.png).
The launch does not verify a post-disclaimer menu, racing scene, or complete
retail parity; existing purple strips remain.

## Redmi black-screen thread sample after PM4 candidate (2026-10-26)

A read-only 5-snapshot `top -H` sample on the installed P2 APK found the
fullscreen still black while the guest main and controller threads each used
about one core. `SHIFT Native GP` was at 0% across the sampled tables; the
renderer vertex/shader thread stayed near idle. This is consistent with the
renderer not receiving sustained work during this interval, but the snapshot
contains no guest ring pointers or submit counters and cannot prove that the
producer stopped. The process remained alive and top-resumed; no input, restart,
or app-data change occurred during this sample.

The [thread evidence](../evidence/process2_redmi_black_idle_threads_20261026.json)
and [raw top sample](../evidence/process2_redmi_black_idle_top_20261026.log.gz)
are attached to the current ARM64 APK/plugin hashes. This shifts the next
cross-process diagnostic toward the guest main/control path while preserving
Process 2's renderer boundary; it is not a renderer parity result.
