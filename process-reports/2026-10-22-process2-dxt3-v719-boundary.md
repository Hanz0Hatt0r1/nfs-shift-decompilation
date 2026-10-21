# Process 2 — managed DXT3 / v719 consumer boundary
Date: 2026-10-22. Scope: existing PR #2143 and supplied v719 evidence only; no P1 code, renderer code, or PR changes.

## Verdict

**PR #2143 supplies the missing Process 2 managed-DXT3 capture capability; it does not, by itself, prove that the exact v719 `unsupported D3D9 managed texture description` stop is cleared.** The P1 managed-texture gate checks `supports_dxt3_texture` for format `0x33545844`; PR #2143 sets that flag in the installed packet-capture adapter. However, the same P1 error can also arise from unsupported descriptor properties, dimension/mip-count checks, or pitch/size validation. The v719 failure's exact texture arguments and a successful post-integration P1 replay have not been demonstrated.

Sources: [P1 managed texture gate](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/work/retail-runtime-d3d9-capture/native_runtime/src/recompiled_pcode_module.cpp); [PR #2143](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2143).

## Existing PR #2143: implementation and tests

- **PR:** [#2143 — Process 2: enable managed DXT3 packet capture](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2143). Status checked 2026-10-22: **open, not merged, mergeable, non-draft**; base `work/retail-runtime-d3d9-capture`; head branch `work/process2-dxt3-capture-capability-20261021`; head commit `121f29537daf4dd5a0098319ebcef370c9510b83` (4 commits; three changed files).
- [`native_vulkan/src/d3d9_packet_capture_adapter.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/121f29537daf4dd5a0098319ebcef370c9510b83/native_vulkan/src/d3d9_packet_capture_adapter.cpp): `D3d9PacketCaptureAdapter::install` sets `adapter.supports_dxt3_texture = true`; existing DDS serializer accepts DXT3 (BC2) and snapshots the exact managed mip bytes on draw-packet capture. This is **capture-only**, not a declaration of direct native Vulkan BC2 texture upload.
- [`native_vulkan/tests/d3d9_packet_capture_adapter_check.cpp`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/121f29537daf4dd5a0098319ebcef370c9510b83/native_vulkan/tests/d3d9_packet_capture_adapter_check.cpp): asserts DXT3 capability; exercises synthetic 8×8 DXT3, two mip levels (64 and 16 bytes); verifies DDS magic, FourCC, top-level size, mip count, byte-identical capture after source mutation, JSONL snapshot path; rejects malformed second-level pitch without a partial snapshot.
- [`.github/workflows/linux-vulkan.yml`](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/blob/121f29537daf4dd5a0098319ebcef370c9510b83/.github/workflows/linux-vulkan.yml): actually executes the focused test with:
  ```sh
  ctest --test-dir native_vulkan/build --output-on-failure --no-tests=error -R '^shift_vulkan_d3d9_packet_capture_adapter$'
  ```

**GitHub Actions state for PR head `121f2953...` (checked 2026-10-22):** [linux-vulkan run 39675686037](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/actions/runs/39675686037) **completed/success**, including the named focused CTest step; [CI run 39675685914](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/actions/runs/39675685914) **completed/success**; [shift-live-dump run 39675686002](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/actions/runs/39675686002) **completed/success**.

## Exact v719 frontier and next owner

The supplied P1 v719 replay used retail PE32 PC 1.02 SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`, running **recompiled P-code over the retail PE**, not native Windows SHIFT.exe. After the P1 D3DX ABI fix (descriptor `Flags` at +0x24, `Bytes` at +0x28), the traced retail accessors returned `Bytes=0x10` for indices 10 and 11. v719 then **blocked** on `unsupported D3D9 managed texture description` with exit 1 at 1,305,017 dispatches; reported `retail_rendering_proven=false`. Its 360 **requested** host frames and dispatch counters are not proof of completed frames, gameplay, draw submissions, or Vulkan rendering. No v719 Draw* entry or native Vulkan consumer submission was demonstrated.

**Next action belongs to Process 1 (integration/producers):** rebuild the corrected D3DX-ABI P1 runtime with the PR #2143 capture adapter installed and `SHIFT_D3D9_PACKET_CAPTURE_DIR` set; record the formerly failing `CreateTexture` descriptor (width, height, levels, usage, pool, format), capability bit and pass/fail result, then trace the first actual guest `DrawIndexedPrimitive` entry/accepted draw packet and callback. If the same texture-description error persists despite DXT3 capability, diagnose P1's remaining descriptor checks before assigning P2 work.

**P2 handoff gate:** once P1 delivers a real accepted draw packet with shader tokens, constant set masks, VB/IB, bound textures/mips and render states, check packet capture → Vulkan bundle/translation → actual `vkQueueSubmit` and validation. Any demonstrated failure *after* callback delivery is a concrete P2 consumer task. **v719 proves none of these draw/Vulkan stages.** No new P2 renderer coding or duplicate DXT3 PR is justified from v719 alone.
