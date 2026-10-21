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
- The capture contains zero 2D or cube texture snapshots.
- The proxy does not capture integer shader-constant updates, so the loop
  control values used by some compiled shaders are not available for execution.
- Target draws use render-target formats 113 (161 draws) and 21 (25 draws),
  while the current bundle contract supports only format 114. The target
  shaders also use between two and five samplers; the current bundle contract
  supports one sampler at s0.

The existing retail replay evidence remains the separate PC capture documented
in [PROCESS_2_D3D9_VULKAN_CAPTURE_REPLAY_20261021.md](PROCESS_2_D3D9_VULKAN_CAPTURE_REPLAY_20261021.md):
one captured SHIFT draw completed native Vulkan validation on GTX 950 and
llvmpipe with zero validation errors. Neither that replay nor these mobile
shader checks claim image parity with a retail frame or Android runtime parity.

The large phone log and payloads remain local rather than being added to Git.

## Verification

- 65 focused capture, shader, bundle, and Vulkan shader tests passed.
- All native Vulkan CMake targets built on Linux.
- The Vulkan validation smoke completed on the GTX 950 with zero validation
  errors and prepared a two-draw bundle set. This generic smoke checks the
  executor only; it is not an NFS SHIFT render or retail-parity evidence.
