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

The Linux XEX run `nfs_shift_073.log` used retail XEX SHA-256
`8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58`. Its log
SHA-256 is
`47750ab5d9e78f4c91b790cfaacb7b9513b440b813aac5727d699e66e2457ea8`.
It selected an NVIDIA GeForce GTX 950 and created 24 graphics-pipeline-state
requests. Those requests alone did not establish a guest draw.

A later diagnostic run, `nfs_shift_082.log` (SHA-256
`911fdac9f31d6c073c28200b133063dc94ad5268d804b655d8190bcb2257b463`), resolved
Vulkan function pointers through `vkGetDeviceProcAddr` and traced dispatch
calls. `vkQueueSubmit` and `vkQueuePresentKHR` returned `VK_SUCCESS`; the
observed `vkWaitForFences` calls also returned `VK_SUCCESS`. This corrects the
earlier timeout snapshot: that single wait was not evidence of a general
renderer deadlock.

The same trace saw twelve `vkCmdDraw` calls on the `GPU Commands` thread and no
`vkCmdDrawIndexed` call. The first call used `vertexCount=3`,
`instanceCount=1`, `firstVertex=0`, and `firstInstance=0`. Its stack was:
`DeferredCommandBuffer::Execute` → `VulkanCommandProcessor::EndSubmission` →
the `IssueSwap` callback → `VulkanPresenter::RefreshGuestOutputImpl` →
`VulkanCommandProcessor::IssueSwap` →
`CommandProcessor::ExecutePacketType3_XE_SWAP`. This establishes that a
deferred Vulkan draw was replayed while the Xenos command processor was
handling a guest `XE_SWAP`. It does **not** identify which earlier guest packet
recorded that deferred draw, prove that it came from `DRAW_INDX`, or establish
its buffers, shader, state, or retail-frame parity. The external Xenos plugin
was used only as a diagnostic oracle here; it is excluded from the intended
product renderer.

The diagnostic process later faulted in generated guest code at
`sub_823A5958` (`nfs_shift_recomp.176.cpp:5091`). That is a separate runtime
failure and is outside this renderer task; no Process 1 source was changed.

## First confirmed retail indexed draw: still diagnostic evidence

A bounded debugger run correlated a guest ring packet with
`VulkanCommandProcessor::IssueDraw` on the GPU command thread. The ring span at
offset `0x2c64` begins with the 20 bytes
`c0 03 22 01 00 00 00 00 00 06 00 04 09 75 d7 b0 40 00 00 06`;
packet dispatch identified it as `PM4_DRAW_INDX`. Reading these Xbox ring bytes
as big-endian dwords gives `c0032201 00000000 00060004 0975d7b0 40000006`.
The parsed draw arguments were primitive 4
(`TRIANGLE_LIST`), six 16-bit indices, guest index base `0x0975D7B0`, and a
12-byte index range. The retained index-memory dump currently contains zeros
because the first capture selected the wrong shared-memory alias; index
contents and vertex payload bytes are therefore not claimed as reproducible
evidence yet.

The same GPU-thread capture records the state and resources consumed by this
draw, rather than merely nearby active-looking registers:

- register-file snapshot SHA-256:
  `fdf06f5a6be53a2077f24ecaebb00931b36d10a98b1786131f6f2bb7c8604f0e`;
- `VGT_DRAW_INITIATOR=0x00060004`, `VGT_DMA_BASE=0x0975D7B0`, and
  `VGT_DMA_SIZE=0x40000006`;
- vertex fetch descriptor 95 resolves to guest address `0x0975DFD0`, with a
  48-byte fetch range; the retained memory dump did not preserve its payload;
- texture fetch descriptor 0 resolves to format 6 (`8_8_8_8`), 1024×256,
  tiled texture storage at guest address `0x09D57000`; texture payload bytes
  are not preserved in the retained capture;
- the draw's VS microcode is 105 dwords at `0x09D568E0` (SHA-256
  `d448760823568068b6f70d903fde9a1faca73c6cfaca7cab59fe73713f1712bc`); its
  fetch instructions reference vertex descriptor 95;
- its PS microcode is 30 dwords at `0x09D50460` (SHA-256
  `5fda214bf53b3f88909fa90c014b9c42de0a3278138df24049af918344489f28`); its
  texture fetch references descriptor 0.

The project now has a narrow C++ decoder for this captured `PM4_DRAW_INDX`
form. It checks the exact type/opcode/length, requires the initiator and DMA
index counts to agree, matches the observed index binding, and emits neutral
triangle-list/index-buffer parameters. Its regression uses the five captured
ring dwords and the `IssueDraw` binding. It does not interpret a general Xenos
register stream, transform index bytes, translate shaders, or issue Vulkan
commands.

This is the first confirmed XEX-originated indexed draw input. Its fetch
metadata indicates a textured resource, but the draw is not identified as a
vehicle draw. The shader, resource and state were observed while the external
Xenos plugin interpreted the ring. That plugin was used only as a diagnostic
oracle and is not part of the product architecture. There is still no
project-owned Vulkan submission of this draw, phone result, or retail parity
claim.

## Local checks

- `shift_xbox_draw_input_check`: passed; covers the captured packet, mismatched
  binding, unsupported opcode, and truncated packet.
- Existing `tools/run_linux_vulkan_smoke.py ... --validation`: rendered the
  neutral bundle on a GeForce GTX 950 with validation enabled and zero
  validation errors. The layer reported three warnings for unused vertex
  attributes 1–3 in that existing smoke shader.
- These checks validate packet decoding and the existing neutral Vulkan path;
  the smoke bundle is not the captured Xbox draw and is not retail parity.

## Next native-renderer work

Next, preserve correct index/vertex/texture bytes and correlate the guest
shader pair to an independent project-owned SPIR-V translation. Then connect
the bounded decoder to buffer/resource preparation and the existing Vulkan
1.1 core. Unsupported packet forms, resource formats, and shader instructions
must fail closed. This is command translation to Vulkan, not shipping an Xenos
command processor or rendering emulator. Keep XCB/Wayland/Android surface
integration outside the shared core. Vulkan validation can prove API
correctness; image and runtime comparisons must separately establish retail
behavior.

## Portability and ownership

Keep the draw translator and Vulkan device/resource core free of XCB, Wayland,
and Android surface types. Reuse the Vulkan 1.1 core and the platform-specific
surface backends already present. A future renderer frontend must not add a
generic Xenos register machine, speculative lighting, or shader features that
are not demanded by the captured SHIFT draw. No Process 1 runtime, P-code,
Ghidra, or guest-scheduler source was changed for this report.

## Limits

This report records a confirmed XEX-originated indexed draw and diagnostic
input evidence. It adds a narrow draw-input decoder, not a complete production
Xbox frontend, and makes no claim of a native Vulkan submission for this draw,
phone rendering, or retail-image parity. The existing native backend remains a
D3D9/neutral-contract renderer until the captured resources and shaders are
translated by project-owned code.
