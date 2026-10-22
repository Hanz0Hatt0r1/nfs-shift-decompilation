# Process 2 — Xenos async-placeholder draw follow-up

Date: 2026-10-22

Scope: the ReXGlue Xenos/Vulkan path for the retail Xbox 360 XEX. This records the nearest renderer-side stop between the reported loading screen and a confirmed guest draw/present. Process 1 runtime, P-code, scheduler, and frontend files were not changed or inspected for implementation.

## Finding

The closest verified renderer blocker is ReXGlue's asynchronous placeholder-pipeline path. For a guest draw whose real Vulkan pipeline is still compiling, `VulkanCommandProcessor::IssueDraw` marks the frame and returns before binding the real graphics pipeline or recording that guest draw. `IssueSwap` then ends the submission and returns before the presenter when both asynchronous compilation and incomplete-frame skipping are enabled.

The exact XEX run log shows that path in action. The inspected NFS checkout contains the D3D9 capture/replay and generic Vulkan bundle code, but its `src/` and `native_vulkan/` file inventory has no Xenos, PM4, guest GPU, or command-processor implementation. The draw code belongs to the external ReXGlue SDK, so this repository has no responsible draw implementation to patch or regression-test. The smallest diagnostic integration change is to append `--no-async_shader_compilation` to the existing Xenos-enabled launch. That makes the pipeline cache create the real pipeline synchronously and avoids the placeholder early return if shader translation and pipeline creation succeed.

## Target and run provenance

- Title: Need for Speed: Shift Europe, Xbox 360, title ID `454108B4`.
- Retail XEX SHA-256: `8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`.
- Runtime: ReXGlue SDK 0.10.0, Linux AMD64, Xenos GPU plugin; the log selects an NVIDIA GeForce GTX 950 Vulkan device.
- Run log: `/home/pes/work/nfsshift-rex/out/build/linux-amd64-release/logs/nfs_shift_066.log`.
- Log SHA-256: `92603b7cc3d2ade90a89575674c0a5b333dc2930c754c9d8699ea32ed7eea7a8`.
- The user reports seeing the original loading screen. There is no screenshot or captured presented frame for that observation.

## Runtime evidence

The exact log contains these events, in order:

```text
135 [23:12:00.204] VulkanPresenter: Created 1536x864 swapchain with format 44, color space 0, presentation mode 0
148 [23:12:00.577] Initializing shader storage for title 454108B4...
152 [23:12:00.664] Created 3 graphics pipelines from Vulkan storage (3 requested)
153 [23:12:00.693] VulkanPresenter: Created 1920x1080 swapchain with format 44, color space 0, presentation mode 0
171 [23:12:02.690] SetInterruptCallback(823B37B8, B7365F00)
213 [23:12:02.986] Creating graphics pipeline state with VS FB19B9A9A727ECB5
215 [23:12:02.990] Creating graphics pipeline state with VS FB19B9A9A727ECB5, PS FB00D39D788098A6
216 [23:12:02.990] Creating graphics pipeline state with VS B6C9863F710683EC
219 [23:12:03.004] Skipping Vulkan frame presentation due to async placeholder draw usage in this frame
929 [23:12:11.606] [FATAL] Call to invalid or unregistered function at guest address 0x82D1BB90
```

The first two pipeline lines at 213 and 215 are guest-derived vertex/pixel shader pipeline-state requests; line 216 requests another vertex-shader state. They establish pipeline-path progress. The explicit warning at line 219 establishes that the frame took ReXGlue's placeholder skip path. Swapchain creation and pipeline lookups do not establish a real guest draw or a host present.

The fatal at line 929 occurred 8.602 seconds later on a different host thread from the placeholder warning. The available trace does not connect that guest fatal causally to the skipped frame. It also provides no evidence that the real pipeline completed or that a later frame was presented before termination. The warning is emitted once per process, so its absence from later log lines would not establish that later frames stopped taking the same branch.

## Source trace in the SDK

The checked source is the ReXGlue `v0.10.0` tag at commit `f5337cdc947ff6d4c4196737e2c807a48f2a1fc2`. The local Android feature-profile worktree has unrelated uncommitted memexport changes; the placeholder/present logic below is unchanged from that tag.

`src/graphics/command_processor.cpp:77-81` defaults `async_shader_compilation` to `true`. `src/graphics/vulkan/command_processor.cpp:58-61` defaults `vulkan_async_skip_incomplete_frames` to `true` and describes its purpose as skipping frames that used placeholder pipelines.

In `src/graphics/vulkan/pipeline_cache.cpp:1114-1115`, asynchronous creation requires the async CVar, worker threads, a pixel shader, and the placeholder shader:

```cpp
bool use_async = REXCVAR_GET(async_shader_compilation) && !creation_threads_.empty() &&
                 pixel_shader && placeholder_pixel_shader_ != VK_NULL_HANDLE;
```

For a new pipeline, lines 1159-1172 mark it as a placeholder, create the placeholder pipeline, and enqueue the real pipeline for a worker. If no async request is queued, lines 1179-1184 create the real pipeline synchronously and clear the placeholder bit.

In `src/graphics/vulkan/command_processor.cpp:3859-3867`, `IssueDraw` reloads the pipeline handle and takes this branch when the current pipeline remains a placeholder:

```cpp
if (REXCVAR_GET(async_shader_compilation) && pipeline_is_placeholder) {
  frame_used_async_placeholder_pipeline_ = true;
  return true;
}
```

This return occurs before the graphics pipeline bind at line 3871 and before the guest draw submission later in `IssueDraw`. The frame flag is reset when a new frame opens (`command_processor.cpp:5318-5320`).

`IssueSwap` at `src/graphics/vulkan/command_processor.cpp:2292-2304` checks all three conditions and takes the early return:

```cpp
bool skip_present_due_async_placeholder = REXCVAR_GET(async_shader_compilation) &&
                                          REXCVAR_GET(vulkan_async_skip_incomplete_frames) &&
                                          frame_used_async_placeholder_pipeline_;
if (skip_present_due_async_placeholder) {
  static bool skipped_incomplete_frame_logged = false;
  if (!skipped_incomplete_frame_logged) {
    skipped_incomplete_frame_logged = true;
    REXGPU_WARN(
        "Skipping Vulkan frame presentation due to async placeholder draw "
        "usage in this frame");
  }
  EndSubmission(true);
  return;
}
```

The `presenter->RefreshGuestOutput` path starts below that return (`command_processor.cpp:2421`). Therefore the warning proves an intentionally skipped presentation for that frame, while the draw early return proves that the placeholder path did not record that guest draw.

`include/rex/cvar_cli.h:21-52` registers each boolean CVar with both `--<name>` and `--no-<name>` forms. The SDL windowed entrypoint calls `rex::cvar::Init(argc, argv)` in `src/ui/windowed_app_main_sdl.cpp:39-42`. This supports the following one-run diagnostic on the existing plugin-enabled launch:

```text
--no-async_shader_compilation
```

Turning off only `vulkan_async_skip_incomplete_frames` would let `IssueSwap` proceed with a partial frame, but `IssueDraw` would still return without recording the placeholder guest draw. That option can probe presentation transport; it cannot satisfy the first-real-draw criterion.

## Next acceptance check and limits

Run the same XEX, SDK, and staged Xenos plugin once with `--no-async_shader_compilation`. Capture a single frame's guest command/ring provenance, confirm the selected pipeline is no longer a placeholder, observe a real `vkCmdDraw*` call and Vulkan queue submission, and record a successful host present for that frame. Preserve a screenshot or readback together with the log. If synchronous shader/pipeline creation fails, the resulting failure log becomes the next renderer frontier.

This diagnostic changes only an existing runtime CVar. It adds no Vulkan feature requirement, API level, host pointer assumption, or window-system dependency, so it does not alter the Vulkan 1.1 or ARM64/Android portability boundary. The captured run is Linux AMD64 on a Vulkan 1.4-capable host; it does not validate the Android surface or a phone draw.

No source implementation or test was added in this repository because the blocker is owned by the external ReXGlue SDK. `git diff --check` is the applicable repository check for this report-only update. The visible loading-screen report remains user observation without captured pixels; this report does not claim retail draw parity, a completed guest draw, or a presented retail frame.
