# Process 2 — Android retail D3D9 capture evidence (2026-10-21)

## Capture

The Redmi Note 14 Pro+ 5G/GameHub run reached a live SHIFT race through the
native D3D9 capture proxy. Wine's `WINEDEBUG=-all` reduced Wine diagnostics;
`DXVK_LOG_LEVEL=error` reduced DXVK log volume. Neither setting captures draw
state by itself—the native D3D9 proxy supplied the graphics evidence.

The local, uncommitted capture is
`/tmp/shift-mobile-capture-20261021/shift_d3d9_capture.jsonl` (50,889,175
bytes; SHA-256
`71ec43893e5706c696757934e47d4cceb5a18b4699f10be589d1c1cd383f6ffb`). Its
separate `buffers/` directory contains 2,124 payload files (15,062,414 bytes).
The raw log parses as 71,634 valid events with no malformed JSON or duplicate
keys, including 2,783 indexed draws. The target-shader audit matched 16 of 51
inventory shaders and found 186 target-shader draws in frames 1569–1571.
Per-pair SPIR-V validation results and capture hashes are recorded in
[`shift_mobile_d3d9_shader_pair_validation_20261021.json`](../evidence/shift_mobile_d3d9_shader_pair_validation_20261021.json).

## Shader translation result

The 186 target draws use 10 distinct captured vertex/pixel shader pairs. All 10
pairs now compile to Vulkan GLSL/SPIR-V and link their stages with
`glslangValidator`. The capture exposed three translation defects on this real
shader set:

- D3D9 `SINCOS` source components were expanded as two whole vectors, producing
  an invalid GLSL vector constructor.
- `LOOP aL, i#` read its loop count and initial/step values from `aL` instead of
  the integer constant register. D3D9 defines these as `i#.x`, `i#.y`, and
  `i#.z` ([Microsoft LOOP reference](https://learn.microsoft.com/en-us/windows/desktop/direct3dhlsl/loop---vs)).
- Unused declared vertex outputs could receive locations already used by linked
  varyings, causing a Vulkan GLSL location collision.

Targeted tests cover each translation path, plus deferred buffer payload
selection. A deferred payload is admitted for a draw only when its recorded
`payload_capture_frame` is strictly earlier than the draw frame; same-frame
deferred payloads fail closed because the log cannot establish their order.

## Replay boundary

This phone capture does not produce a replay bundle:

- None of the 186 target draws has both a matching captured vertex-buffer and
  index-buffer payload.
- After the D16 mapping, the bundle builder reaches the first target draw
  (event 4926423) and rejects it because its vertex buffer has no matching
  captured Lock-range payload.
- The capture contains zero 2D or cube texture snapshots.
- The proxy does not capture integer shader-constant updates, so the loop
  control values used by some compiled shaders are not available for execution.
- Target draws use render-target formats 113 (161 draws) and 21 (25 draws).
  The Vulkan bundle now maps 113 to `VK_FORMAT_R16G16B16A16_SFLOAT` and 21 to
  `VK_FORMAT_B8G8R8A8_UNORM`; format 114 (`VK_FORMAT_R32_SFLOAT`) remains
  supported for the separate PC capture. The capture bundle now collects each
  active 2D sampler register separately; the shared packet and native executor
  accept s0–s15. The target shaders use s0–s4, and a regression serializes all
  five registers into one packet.
- All 186 target draws have their shader-used texture stages bound and have the
  five sampler-state values currently required by the converter. They still
  have no texture snapshots. The captured sampler values also expose follow-up
  Vulkan work: 126/186 draws use D3D9 border addressing on s0 (address mode 4,
  with captured border colors 0x00000000 or 0xffffffff), and 10/186 use
  anisotropic min/mag filtering on s1 with max anisotropy 6. The capture also
  records a 1.0 mip LOD bias and sRGB-texture enablement on some stages; the
  current packet converter does not preserve those states or mip chains. The
  multi-register change is descriptor-binding support, not complete replay of
  those captured sampler contracts.

The phone capture triggered at `Present` in frame 1571, after target draws from
frames 1569–1571 had already executed. Their `SetTexture` rows therefore kept
`snapshot_status=deferred-until-trigger`. The first target draw can be captured
earlier by resource-triggering on its pixel shader, `ps:58462f91650cef34`:
that `SetPixelShader` is event 4926411/frame 1569, before the first target draw
at event 4926423. Across all 186 target draws, each shader-used texture stage
is rebound after its `SetPixelShader` call, so the early trigger activates
texture snapshots before those `SetTexture` calls. The next capture should
also pass `--partial-buffer-payloads` to the capture launcher. The Vulkan
bundle reconstructs a buffer only when ordered captured ranges cover every
byte. The proxy keeps deferred discard writes separate from normal writes,
and the bundle applies ranges in capture order, invalidates older ranges after
`D3DLOCK_DISCARD`, and rejects holes or same-frame ordering ambiguity. The
bundle also requires `device_hooks` to confirm partial capture and a length
filter that includes each buffer; complete-looking bytes from an older
full-only capture cannot prove that no later partial Lock was missed. The exact
trigger and range-mode facts are recorded in the evidence JSON.

The first target draw's depth surface is D3DFMT_D16 (80), mapped to Vulkan
`VK_FORMAT_D16_UNORM` with a depth-only image aspect. Microsoft lists 80 as
D3DFMT_D16, and Khronos defines D16_UNORM as a 16-bit normalized depth format
([D3DFORMAT](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dformat),
[Vulkan format reference](https://docs.vulkan.org/refpages/latest/refpages/source/VkFormat.html)).

The native Vulkan executor also passed a format smoke for 21 and 113 on a GTX
950 with zero validation errors. It used the existing synthetic material bundle
to exercise attachment creation and readback; it is not an NFS SHIFT draw or
retail-image evidence. PPM output converts half-float channels to clamped
8-bit RGB and swizzles BGRA for inspection only. A synthetic D16 depth-attachment
smoke also rendered with zero Vulkan validation errors; it validates the
attachment mapping, not the captured SHIFT draw.

The existing retail replay evidence remains the separate PC capture documented
in [PROCESS_2_D3D9_VULKAN_CAPTURE_REPLAY_20261021.md](PROCESS_2_D3D9_VULKAN_CAPTURE_REPLAY_20261021.md):
one captured SHIFT draw completed native Vulkan validation on GTX 950 and
llvmpipe with zero validation errors. Neither that replay nor these mobile
shader checks claim image parity with a retail frame or Android runtime parity.

The large phone log and payloads remain local rather than being added to Git.

## Verification

- 65 focused capture, shader, bundle, and Vulkan shader tests passed before the
  multi-register change. The current targeted bundle, sampler, executor, and
  native capture-proxy regression set passed 62 tests.
- All native Vulkan CMake targets built on Linux.
- The 11 focused bundle-format and native executor contract tests passed; the
  synthetic format smoke passed for both mobile target formats.
- A separate synthetic five-sampler packet rendered on the GTX 950 with
  validation enabled, five texture descriptors bound, and zero validation
  errors. The general Linux Vulkan smoke also rendered and prepared its
  two-draw bundle set. Both are executor checks, not captured SHIFT renders or
  retail-image parity evidence.
- Partial buffer payload reconstruction passed regressions for out-of-order
  ranges, overlapping later writes, missing coverage, discard invalidation,
  and ambiguous ordering.
