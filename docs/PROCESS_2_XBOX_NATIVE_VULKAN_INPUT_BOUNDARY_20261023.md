# Process 2 — Xbox native Vulkan input boundary (2026-10-23)

## Decision

The Xbox 360 build cannot be connected to the current native Vulkan backend by
redirecting each recompiled guest call as though it were a D3D9
`DrawIndexedPrimitive` call. The recompiled XEX initializes an Xbox GPU command
ring; the game then writes Xenos command packets and GPU state into that ring.
The project-owned renderer needs a narrow, evidence-backed frontend at that
boundary which translates the title's actual draw inputs into the existing
neutral render contract. The production path must not load or depend on
`rexgpu-xenos` or another Xenos GPU emulator.

This report does not add a packet format from guesswork. No raw ring capture or
confirmed XEX-originated indexed draw is available in the evidence reviewed
here, so shader, register, resource, and draw semantics are not yet safe to
implement.

## Source and branch baseline

- The remote `main` tip at review time was `53d82df46d6a4fe69ae7e52d2750fa00d5477d7e`.
- The Process 2 native renderer branch is `work/process2-native-vulkan` at
  `53263b40`; its README already records the absence of an Xbox/Xenos frontend.
- The local `/home/pes/nfs-shift-decompilation` checkout was 142 commits behind
  that remote tip and contained unrelated user files. It was not modified.
- The external ReXGlue SDK checkout had user-owned, uncommitted Android Vulkan
  and shader changes. It was inspected read-only; no SDK files were changed.

## What the Xbox input actually looks like

The generated Xbox title registers these guest video-service imports:

- `VdEnableRingBufferRPtrWriteBack` at import `0x83063D2C`;
- `VdInitializeRingBuffer` at import `0x83063D3C`;
- `VdSetGraphicsInterruptCallback` at import `0x83063DBC`.

The existing Process 2 XEX report records a 4 KiB command ring and a guest
read-pointer write-back address from an observed run. Those are ring setup
arguments, not draw calls. The Xbox guest does not expose the PC D3D9
`DrawIndexedPrimitive` boundary used by the checked-in PC capture bundles.

In the pinned ReXGlue interface, `IGraphicsSystem` receives the ring pointer and
size through `InitializeRingBuffer(ptr, size_log2)`. Its Xenos plugin forwards
that service to a Xenos command processor, which consumes the ring and models
Xbox GPU state. Shipping that plugin as the renderer would retain the GPU
emulation that this project is explicitly excluding. A project-owned frontend
can instead consume only the command subset proven by a real SHIFT capture and
translate it into Vulkan draws; it should fail closed on unsupported packets.

## What the existing renderer and captures prove

The current remote `main` and Process 2 branch contain a Vulkan 1.1 native core
with a headless execution path, neutral geometry/resource packets, shader
translation and interface validation, and separate Android and XCB surface
backends. `native_vulkan/README.md` states that the core accepts D3D9 capture
bundles and neutral SHIFT render packets, not PM4 ring data or Xenos shader
microcode.

The raw D3D9 intake and renderer audits (`PHASE600_RAW_D3D9_CAPTURE_AUDIT`,
`PHASE621_RENDERER_FRONTIER_AUDIT`, and
`PHASE633_REGENERATED_RENDERER_BASE_AUDIT`) analyze PC D3D9 captures, shader
bindings, resources, and draw-local state. The replay builder emits
`SHIFT.D3D9CaptureVulkanBundle/1`; the generic path consumes
`SHIFT.VulkanDrawBundle/1` / neutral `RenderCommand/1`. The shader translator
parses D3D9 shader tokens. None of those contracts carries a PM4 ring span or
Xenos microcode.

The retail `DrawIndexedPrimitive` replay documented in
`docs/PROCESS_2_D3D9_VULKAN_CAPTURE_REPLAY_20261021.md` proves one PC D3D9 draw
can be translated and submitted with Vulkan validation enabled. The Android
capture documented in `docs/PROCESS_2_ANDROID_D3D9_CAPTURE_20261021.md` is also
a D3D9 capture path. Neither is an Xbox XEX command-stream capture; neither
specifies the Xbox shader bytecode, register writes, fetch descriptors, GPU
addresses, target setup, or packet ordering. Those captures are useful as
examples for the neutral renderer boundary, not as substitutes for Xbox draw
evidence.

The Linux Vulkan workflow and the current Vulkan draw/bundle tests exercise the
neutral packet and D3D9 replay paths. They do not consume an Xbox ring buffer,
so a green result from them cannot validate an Xbox frontend.

## Latest Xbox run: diagnostic evidence only

The Linux XEX run `nfs_shift_073.log` is tied to the retail XEX SHA-256
`8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`. Its log
SHA-256 is
`47750ab5d9e78f4c91b790cfaacb7b9513b440b813aac5727d699e66e2457ea8`.
It selects an NVIDIA GeForce GTX 950 and creates 24 graphics-pipeline-state
requests. These requests show activity in the external Xenos/Vulkan diagnostic
path; they do not establish a guest draw, its input resources, a successful
Vulkan draw command, or a presented retail frame. This path was used only to
inspect the current stopping point and is not the intended renderer
architecture.

In the timeout debugger snapshot, breakpoints on `vkCmdDrawIndexed`,
`vkCmdDraw`, and `vkQueuePresentKHR` resolved but were not hit. The UI thread
was waiting in `VulkanSubmissionTracker::AwaitSubmissionCompletion`; the
observed stack alone does not identify which of the presenter's several waits
was active. The previous debugger run did not instrument `vkQueueSubmit`, so it
cannot distinguish a successfully submitted presenter-only command buffer
from a missing submit, a stalled fence, or a draw on another command path.

The source trace narrows that diagnostic:

- `VulkanSubmissionTracker::AwaitSubmissionCompletion` may call
  `vkWaitForFences` with `UINT64_MAX` on a pending submission fence.
- `VulkanPresenter::PaintAndPresentImpl` has several waits; it submits its own
  swapchain command buffer at `vkQueueSubmit` and calls `vkQueuePresentKHR`
  later in the function.
- The stack snapshot does not establish the active wait site or connect the
  waited fence to a guest-originated draw.

Therefore the timeout is not evidence that pipeline compilation deadlocked,
that the guest drew successfully, or that the GPU is stuck on a retail draw.

## Next discriminating capture

On a diagnostic run, capture one correlated timeline for
`vkQueueSubmit`, `vkWaitForFences`/`vkGetFenceStatus`, and
`vkQueuePresentKHR`, including timestamp, host thread, queue, fence, result,
and the stack at each call. If a fence wait is reached, identify the matching
submit and its command-buffer count. This will classify the current presenter
wait without changing Process 1 files or modifying the user's SDK worktree.

In parallel, the first renderer-input acceptance artifact must be a
guest-originated command-ring snapshot correlated to a real indexed draw. It
must retain the raw packet span and source provenance, index/vertex fetch
inputs, shader microcode and constants, texture/resource bytes, render-target
and depth state, viewport/scissor, and the associated swap/resolve boundary.
Only then should a minimal `XenosDrawSnapshot/1`-style bridge be made a stable
contract and translated into existing neutral Vulkan inputs. Synthetic draws
and Xenos-emulator pipeline requests do not satisfy that acceptance check.

## Portability and ownership

Keep the draw translator and Vulkan device/resource core free of XCB, Wayland,
and Android surface types. Reuse the Vulkan 1.1 core and the platform-specific
surface backends already present. A future renderer frontend must not add a
generic Xenos register machine, speculative lighting, or shader features that
are not demanded by the captured SHIFT draw. No Process 1 runtime, P-code,
Ghidra, or guest-scheduler source was changed for this report.

## Limits

This report records an architecture boundary and diagnostic plan. It adds no
Xenos packet translator and makes no claim of an Xbox guest draw, Vulkan draw
submission, phone rendering, or retail-image parity. The existing native
backend remains a D3D9/neutral-contract renderer until the Xbox draw inputs are
captured and translated.
