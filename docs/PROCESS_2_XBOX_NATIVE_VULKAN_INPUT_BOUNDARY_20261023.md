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

The evidence below now contains one correlated XEX-originated `PM4_DRAW_INDX`
packet, its resources, shaders, and a register-file snapshot. The project-owned
frontend decodes only those captured packet, descriptor, texture-layout,
sampler, and target/scissor forms. It still does not translate the captured
shaders, allocate a native target, or submit this draw.

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

## First confirmed retail indexed draw: captured inputs, still diagnostic evidence

A bounded debugger run correlated a guest ring packet with
`VulkanCommandProcessor::IssueDraw` on the GPU command thread. The ring span at
offset `0x2c64` begins with the 20 bytes
`c0 03 22 01 00 00 00 00 00 06 00 04 09 75 d7 b0 40 00 00 06`;
packet dispatch identified it as `PM4_DRAW_INDX`. Reading these Xbox ring bytes
as big-endian dwords gives `c0032201 00000000 00060004 0975d7b0 40000006`.
The parsed draw arguments were primitive 4
(`TRIANGLE_LIST`), six 16-bit indices, guest index base `0x0975D7B0`, and a
12-byte index range. A corrected, bounded GDB run read the guest shared-memory
mapping at `0x200000000 + guest_address` and retained the actual bytes outside
the repository. The six raw index values are
`00 00 00 01 00 02 00 02 00 01 00 03`; this draw's captured 8-in-16 endian mode
normalizes them to Vulkan UInt16 indices `[0, 1, 2, 2, 1, 3]`.

The same GPU-thread capture records the state and resources consumed by this
draw, rather than merely nearby active-looking registers:

- latest register-file snapshot SHA-256:
  `a0718a1b2044da9698c3f715c4ff319ae7a8d785fb8809c46f090beff9a19225`;
- `VGT_DRAW_INITIATOR=0x00060004`, `VGT_DMA_BASE=0x0975D7B0`, and
  `VGT_DMA_SIZE=0x40000006`;
- vertex fetch descriptor 95 has raw words `0x0975DFD3, 0x10000032`: guest
  address `0x0975DFD0`, 8-in-32 endian mode, and 12 words (48 bytes). The
  retained payload SHA-256 is
  `5616b2becd40c3011eb1ab0c28a8a3b194fe8c966aec84c056915353a6f31c2d`; its
  bytes decode to four float3 positions `(-1,-1,0)`, `(1,-1,0)`, `(-1,1,0)`,
  `(1,1,0)`;
- texture fetch descriptor 0 resolves to format 6 (`8_8_8_8`), 1024×256,
  tiled texture storage at guest address `0x09D57000`; the captured 1 MiB
  payload SHA-256 is
  `89ee6d3ffcbeeb27a6b76c70699de59e1037f7e387fe7a487b84ed65c11ca4c4`;
  descriptor words are `8800d8fe 09d57086 001fe3ff 01280c14 00000003
  00000a10`, with 8-in-32 endian mode and packed swizzle `0x60A`;
- the captured 12-byte index payload SHA-256 is
  `a305c49db5906a669149e9889c39043ec60e071b423c97f8df2b75cc33cc274c`;
- the draw's VS microcode is 105 dwords at `0x09D568E0` (SHA-256
  `d448760823568068b6f70d903fde9a1faca73c6cfaca7cab59fe73713f1712bc`); its
  fetch instructions reference vertex descriptor 95;
- its PS microcode is 30 dwords at `0x09D50460` (SHA-256
  `5fda214bf53b3f88909fa90c014b9c42de0a3278138df24049af918344489f28`); its
  texture fetch references descriptor 0.

The register snapshot is a little-endian register-file image. Using the public
Xenia register map and field definitions to name the captured addresses, the
observed target state is `RB_SURFACE_INFO=0x14000500`,
`RB_COLOR_INFO=0x00010000`, `RB_DEPTH_INFO=0x000002d0`,
`RB_MODECONTROL=4`, `RB_DEPTHCONTROL=0x00700770`, and `RB_COLOR_MASK=0xf`.
The viewport words decode to X scale/offset 640/640 and Y scale/offset
-360/360, so the target extent is 1280x720 with inverted Y. The window scissor
registers are `PA_SC_WINDOW_SCISSOR_TL=0` and
`PA_SC_WINDOW_SCISSOR_BR=0x02d00500`, or (0,0)-(1280,720); the screen scissor
is (0,0)-(8192,8192). The captured scissor therefore has area. Register names
are cross-checked against the public [Xenia register map](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/register_table.inc)
and [register fields](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/registers.h),
documentation only, with no Xenia runtime dependency.

The same snapshot also retains the constants required by the exact shader pair.
`SQ_VS_CONST=0x000ff000` sets the VS base to float4 0; `SQ_PS_CONST=0x000ff100`
sets the PS base to float4 256. Thus the PS's `c0` and `c255` refer to physical
float-bank entries 256 and 511. The packed bool bank has
`0x4904=0x00000001`, which resolves `b128=true` and `b129=false`. Combined with
the captured PS disassembly, the `!b128` jump is not taken (the texture fetch
runs), and the `!b129` jump is taken to label L4. The project-owned constants
decoder now resolves only the captured pair's `c64-c69`, `c254-c255`, PS
`c0/c255`, and `b128/b129`; it emits no shader code. The bank mapping and
conditional-jump fields are cross-checked against public Xenia
[`command_processor.cc`](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/command_processor.cc)
and [`ucode.h`](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/ucode.h),
documentation only.

Read-only disassembly of that captured pair narrows the independent translator
needed for this draw:

- the VS fetches descriptor 95 as `FMT_32_32_32_FLOAT`, stride 3, then computes
  clip position from float constants 64–67 and interpolator 0 from constants
  68–69;
- the PS executes `tfetch2D` from descriptor 0 and writes color through the
  captured conditional path (`b128`/`b129`).

For comparison only, the external Xenos plugin's `EnsureShadersTranslated`
boundary produced SPIR-V modules with SHA-256
`d27ca93242a83ccb67613b53243bd4531fbf56783770bc14adc71cfd2791ad29` (VS) and
`6c0ec0128dddd1522492363c8f68bc0648798af4544d97033fdad13284a78a7d` (PS).
Both modules declare SPIR-V 1.5; `spirv-val --target-env vulkan1.1` rejects
them because Vulkan 1.1 accepts SPIR-V only through 1.3. These temporary
reference modules were kept outside the repository and are not an acceptable
product dependency. The project needs its own shader translation that emits
Vulkan 1.1-compatible SPIR-V and consumes project-owned resource/state
contracts. Header-only downgrade probes are also invalid: changing the version
to 1.3 exposes the optional `SignedZeroInfNanPreserve` float-control
requirement. Adding `SPV_KHR_float_controls` still leaves SPIR-V 1.3 interface
rules violated by the diagnostic module's Uniform variables in `OpEntryPoint`.
Vulkan 1.1 can
expose float-control modes through the optional
[`VK_KHR_shader_float_controls` extension](https://github.com/KhronosGroup/Vulkan-Docs/blob/main/appendices/VK_KHR_shader_float_controls.adoc),
so a project-owned emitter must generate a valid module and gate those modes on
the target device's advertised support. Probe details are in
`evidence/process2_xbox_shader_vulkan11_gate_20261023.json`.

The project-owned shader-input decoder now also frames the bounded control-flow
prefix of this exact Xbox bytecode. It unpacks two 64-bit control-flow records
from each 96-bit big-endian triplet, using the first `exec`-family address as
the same documented upper-bound heuristic used by the public Xenia
[`ucode.h`](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/ucode.h)
decoder.
The captured VS yields 10 slots (five `exec` clauses, two output allocations,
`exece`, and `cnop`); the PS yields eight slots (three conditional jumps,
three `exec` clauses, color allocation, and `exece`). The PS jump records retain
the captured `b128` / `b129` predicates and the unconditional jump to slot 6.
This remains input parsing only: ALU fields are decoded, but their operations
are not interpreted or translated, and no shader is executed. Exact raw-byte hashes
and decoded fields are recorded in
`evidence/process2_xbox_shader_control_flow_20261023.json`.
The first scheduled fetch instructions are separately decoded: VS address 5
resolves to `vfetch_full` descriptor 95 (format `0x39`, three dwords stride),
and PS address 4 resolves to `tfetch2D` descriptor 0 with a 2D dimension. The
fetch decoder reads fields only; it does not access guest memory. Its evidence
is in `evidence/process2_xbox_shader_fetch_20261023.json`.
The project also extracts raw fields from the scheduled ALU triplets: 28 in the
VS and four in the PS. The record includes raw vector/scalar opcodes,
destinations, masks, sources, swizzles, and predicate bits. These opcodes have
not been assigned execution semantics or translated; the field histograms are
in `evidence/process2_xbox_shader_alu_fields_20261023.json`.
The schedule expansion is project-owned: it emits 29 VS instruction addresses
and five PS addresses from the captured `exec` clauses, classifies their ALU or
fetch slots, and retains the serialized bit. It leaves conditional jumps
unevaluated, so the PS branch alternatives remain separate clauses. Details
are in `evidence/process2_xbox_shader_schedule_20261023.json`.

The project now has a narrow C++ decoder for this captured `PM4_DRAW_INDX`
form. It reads topology, DMA source, 16-bit index format, guest address,
count, and swap mode directly from the packet; it does not need the
`IndexBufferInfo` object produced by the diagnostic plugin. It requires the
initiator and DMA counts to agree and emits neutral triangle-list/index-buffer
parameters. Bounded descriptor decoders read the captured vertex fetch 95 and
texture fetch 0 directly from their register words and check the observed
address, format, dimensions, tiling, endian mode, and sampling fields. A byte
normalizer handles only the two captured buffer orders (8-in-16 indices and
8-in-32 vertex words). The exact 1024x256 texture layout is untiled to linear
texel order with its captured 8-in-32 byte swap. The sampling decoder maps the
captured swizzle, channel signs, clamps, filters, anisotropy, and border code
to semantic values; it rejects reserved selector values. A bounded raster
decoder maps the captured single-sample 1280x720 gamma RGBA8/D24S8 target,
centered viewport, write/depth enables, and intersected scissor. A shader
constant decoder applies the captured VS/PS constant bases and resolves the
constants read by this shader pair, including its pixel-shader branch values.
It does not map Xenos EDRAM tile storage to a Vulkan image, create a pipeline,
translate microcode, or emit SPIR-V. Border code 0 has unresolved alpha, so the
Vulkan border color is not guessed. Regressions cover
the captured packet and descriptors, layout boundaries, byte order, sampling
semantics, and unsupported or truncated inputs. The code does not interpret a
general Xenos register stream, translate shaders, or issue Vulkan commands.

The contiguous 19,784-byte ring snapshot was then scanned with project-owned
packet framing. It consumes all 247 packets (162 type 0, zero type 1, 21 type 2,
64 type 3) and finds four `PM4_DRAW_INDX` spans at `0x2c64`, `0x3614`, `0x3fec`,
and `0x49ec`. Each span passes the bounded draw decoder: the first three use six
indices at guest address `0x0975D7B0`; the fourth uses 60 indices at
`0x09D55170`. The captured stream SHA-256 is
`8797c590bda56ab0cd76837832c1eea6519a161a60c54f6a0f2f32396cba7379`. The raw
ring remains outside the repository. This scanner reports packet framing and
type-3 opcodes only; it does not apply register writes, synchronize a live ring,
or emulate the GPU. Packet framing, including zero-dword NOP handling, is
cross-checked against public Xenia
[`command_processor.cc`](https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/command_processor.cc)
for documentation only; no Xenia runtime code is used. Evidence is recorded in
`evidence/process2_xbox_pm4_stream_20261023.json`.

This is the first confirmed XEX-originated indexed draw input. Its fetch
metadata indicates a textured resource, but the draw is not identified as a
vehicle draw. The shader, resource and state were observed while the external
Xenos plugin interpreted the ring. That plugin was used only as a diagnostic
oracle and is not part of the product architecture. There is still no
project-owned Vulkan submission of this draw, phone result, or retail parity
claim.

## Local checks

- `shift_xbox_draw_input_check`: passed; covers the captured packet, mismatched
  binding, target format/viewport/scissor state, shader constant addressing and
  branch values, bounded shader control-flow, instruction schedule, fetch, and
  raw ALU-field decode, unsupported opcode/layout/sampling values, non-zero
  window offsets, and truncated input.
- The new CF decoder passed on the exact private VS/PS byte captures; observed
  CF/fetch/ALU fields match their diagnostic disassembly. This validates parsing
  only; no shader-body translation was tested.
- The input decoder, shader control-flow parser, captured fetch-instruction
  parser, and raw ALU-field parser passed as an arm64-v8a binary on the connected
  Redmi Note 8 Pro (Android API 33; binary built with API 29 minimum).
- `tools/run_linux_vulkan_smoke.py ... --validation`: the neutral synthetic BMW
  bundle ran on a GeForce GTX 950 with Vulkan 1.1 validation enabled and zero
  validation errors. It is not the captured Xbox draw and is not retail parity.

## Next native-renderer work

Next, translate the captured shader's ALU operations into project-owned SPIR-V, then
connect the existing ReXGlue guest graphics-service boundary to a project-owned
ring consumer and add evidence-backed register/resource state tracking for the
scanned span. A diagnostic run with `gpu_plugin` unset ignores
guest ring setup services, so this project path still needs an adapter that
loads in ReXGlue and consumes guest ring memory. The adapter must call the
project's packet scanner and native Vulkan frontend directly; it must not route
the product through `rexgpu-xenos` or another GPU emulator. After ring progress
and draw state are consumed natively, resolve the captured texture's Vulkan
view/sampler conversion and EDRAM target mapping, translate the exact guest
shader pair to project-owned Vulkan 1.1-compatible SPIR-V, and submit the draw.
Unsupported packet forms, resource formats, state, and shader instructions
must fail closed. Keep XCB/Wayland/Android surface integration outside the
shared core. Vulkan validation proves API correctness; image and runtime
comparisons must separately establish retail behavior.

## Portability and ownership

Keep the draw translator and Vulkan device/resource core free of XCB, Wayland,
and Android surface types. Reuse the Vulkan 1.1 core and the platform-specific
surface backends already present. A future renderer frontend must not add a
generic Xenos register machine, speculative lighting, or shader features that
are not demanded by the captured SHIFT draw. No Process 1 runtime, P-code,
Ghidra, or guest-scheduler source was changed for this report.

## Limits

This report records a confirmed XEX-originated indexed draw and diagnostic
input evidence. It adds bounded packet framing and draw-input decoders, not a
live ring consumer or a complete production Xbox frontend, and makes no claim
of a native Vulkan submission for this draw, phone rendering, or retail-image
parity. The existing native backend remains a D3D9/neutral-contract renderer
until the captured resources and shaders are translated by project-owned code.
