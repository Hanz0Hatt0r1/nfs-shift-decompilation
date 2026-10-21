# Process 2 — DXT3 retail resource / Vulkan admission audit (2026-10-21)

## Scope and decision

**Result:** Managed DXT3 byte capture is a producer capability, not proof of Vulkan resource upload, of a replay-ready guest draw, or of retail rendering. A deterministic **DXT3 resource-transcode regression** is technically possible with the current GitHub sources; an **original retail DXT3-bound draw validation** is blocked by missing P1 guest draw evidence and absent original payload bytes in the accessible GitHub tree.

Process 2 has made an **independent graphics-only change** in draft PR [#2144](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2144), branch `work/process2-dxt3-vulkan-resource-20261021` based on `main`. PR #2143 was not edited. No Process 1 runtime, Win32 compatibility, P-code or public ABI files were edited. This report is separate from that code PR and lives in the existing `work/process-reports` branch.

## Checked GitHub refs and evidence

- Retail source: original `SHIFT.exe` 1.02 PE32 x86, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.
- Raw original-process capture SHA-256 from PR #2143: `db71d32484c35d97c2aa8645d8f439376d7c1caaaca6041aa565f7549870625b`.
- Retail `CreateTexture` event **2691/frame 20**: 1024×512, one mip, usage 0, `D3DFMT_DXT3 = 861165636 = 0x33545844`, `D3DPOOL_MANAGED = 1`.
- Retail texture payload event **37037/frame 281**: DXT3 512×512, **pitch 2048 compressed bytes per block-row**, **byte_size 262144**, SHA-256 `3148e693a19b0d95a2a021dea80ff78c93b42ec366e4a1b6b31b9e14638e5f96`. The two observations do **not** by themselves establish that these are the same texture object, or that either texture is sampled by a specific DIP.
- Resource shape check: 512/4 = 128 BC2 blocks per block-row; 128 × 16 = **2048** bytes per block-row; 512/4 = 128 block-rows; 2048 × 128 = **262144** compressed bytes. The full RGBA8 base level is 512 × 512 × 4 = **1048576** bytes.
- P1 v662 unsupported-managed-texture-description blocker is no longer encountered according to supplied v666 evidence. The host-frame-loop reached 1440 frames, 44,964,062 guest dispatches and 6,625 unique functions, **but `guest_draw_translation=false` and `retail_rendering_proven=false`**. Those counters are not a frontend/gameplay or rendering proof.
- PR [#2143](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2143) `work/process2-dxt3-capture-capability-20261021`, head `1fef18a8fdc8308365761a901b5e47db91af7e20`, open, targeting `work/retail-runtime-d3d9-capture`. Its exact patch adds **only** `adapter.supports_dxt3_texture = true` and a regression assertion in `native_vulkan/src/d3d9_packet_capture_adapter.cpp` and `native_vulkan/tests/d3d9_packet_capture_adapter_check.cpp`; the existing DXT3 DDS writer recognizes `kDxt3 = 0x33545844`. It does not implement native BC2 upload or demonstrate Vulkan submission. GitHub CI, linux-vulkan and shift-live-dump workflow runs on that head completed successfully. The PR base has moved since its parent commit (compare shows one behind/one ahead), so keep its diff narrow rather than layering new renderer work into it.
- The earlier P2 capture adapter PR #2141 is closed; subsequent P1 branch references are not identical to `main`. P2 resource code in PR #2144 intentionally starts from `main` and does not rebase/overwrite P1.

## Actual resource path and concrete defect

```text
guest managed DXT3 level bytes (P1 packet owned, callback lifetime only)
    -> P2 d3d9_packet_capture_adapter.cpp::dds_bytes (DDS FOURCC DXT3)
    -> D3D9 capture JSONL set_texture(snapshot_paths, stage, identity)
    -> vulkan_d3d9_capture_bundle.py::_capture_texture_packet
    -> texture_reference.py::decode_dds (software BC2 -> RGBA8)
    -> vulkan_texture_packet.py::build_vulkan_texture_packet
    -> SVTP/1: 512×512, one RGBA8 base level + sampler mode
    -> native_vulkan/src/vulkan_bundle_execute.cpp (VK_FORMAT_R8G8B8A8_UNORM/SRGB)
```

The existing Vulkan executor consumes **RGBA8**, not DXT3 block bytes. Therefore, for this **single-mip resource** it does **not** require `VK_FORMAT_BC2_UNORM_BLOCK` native feature support as long as the existing CPU decode-to-RGBA8 path is used. `native_vulkan/include/shift_vulkan_d3d9_packet_capture.hpp` and the P1 callback/lifetime boundary remain unchanged. `SVTP/1` record fields are `register,width,height,pixel_offset,pixel_bytes,sampler_mode`; DXT3 identity is provenance upstream, not a compressed native upload format.

**Found P2 correctness defect:** `texture_reference.py::_decode_dxt3_block` delegated its BC2 color segment to `_decode_dxt1_block`. In DXT1/BC1, `color0 <= color1` selects a three-color+transparent palette; in DXT3/BC2 and DXT5/BC3 it **must** always select the four-color palette, independently of the alpha block. The old decoder could silently turn DXT3 selector #3 RGB into black on legal endpoint orderings. The earlier DXT3 alpha test exercised only selector 0 and did not catch this.

Draft P2 PR **#2144** fixes this via an explicit four-color switch for BC2/BC3 while preserving BC1 three-color transparency. It adds:
1. Regressions for `color0 < color1`, selector 3 and DXT3 explicit 4-bit alpha, plus DXT5 companion and DXT1 control.
2. A synthetic but **retail-shaped** 512×512 / pitch 2048 / 262144-byte one-mip DXT3 DDS fed through the real `_capture_texture_packet` to `SVTP/1`. The test checks binding s0, decoded RGBA8 size 1048576, BC2 RGB+alpha result, sRGB sampler mode and raw DDS provenance hash generated from that **synthetic** fixture.
3. Fail-closed truncation regression. **It does not verify the original retail payload hash** because the original compressed payload is not present in the GitHub inputs.

The new tests were committed through GitHub only. GitHub Actions on PR #2144 head `3e6b6eb4a3d9c32dddd51a6b998ac4f0ed0e8dbe` completed successfully: `CI`, `linux-vulkan` and `shift-live-dump`; CI's `python` job reports a successful **Run complete Python suite** step (so the newly added Python regression tests are covered by that suite). `linux-vulkan` also reports a successful software-stack build and existing headless Vulkan probes. None of those results is a native Vulkan submission of a P1 DXT3 guest draw or a comparison against the original retail payload. No separate local execution, P1 live guest callback or retail image parity is claimed. The previous P2 focused replay evidence proves other selected original draws can reach Vulkan, but not the P1 DXT3 packet path.

## Minimal missing capture fields to prove an actual DXT3 draw

For **resource byte provenance** (no draw needed): provide a packet-bound `guest_texture`, `guest_device`, create/update/release lifetime or generation, `width`, `height`, `levels`, `usage`, `format=0x33545844`, `pool=1`; for each mip: `level`, `width`, `height`, `pitch`, exact owned `bytes` with raw per-level SHA-256. The producer must prove the bytes are the current version at the relevant packet sequence, not an unrelated retail capture or stale address reused after release. P2 copies synchronous packet-owned vectors before callback return. Compare SHA-256 to the supplied original hash **only if the exact original resource/payload is actually the same source**; matching dimensions/FourCC alone does not establish identity.

For **render admission / actual DIP** additionally need, together in **one ordered P1 `DrawIndexedPrimitive` callback**:

- `packet.version`, `guest_device`, monotonic per-device `sequence`, and exact DIP fields `primitive_type`, `base_vertex_index`, `min_vertex_index`, `num_vertices`, `start_index`, `primitive_count`.
- Sixteen stream bindings with guest VB IDs, stride, offsets, **frequencies** and resource descriptions; guest IB identity/size/format/usage/pool; complete current VB/IB bytes from adapter create/update, including unambiguous `D3DLOCK_DISCARD`/partial update history (or full post-unlock snapshot).
- Vertex declaration original elements; bound VS and PS tokens; float and BOOL register arrays **with register validity/set masks or proven complete-state semantics**; BOOL HRESULT if that is the exported packet flavor. These P1 packet-v1 flavors must be compiled from one exact header, not assumed binary equivalent.
- `textures` list with DXT3 `stage` and `guest_texture` identity at the draw; **the shader must actually sample that bound stage**. Give all mip descriptors/owned bytes for guest-managed textures, and clearly distinguish backend-owned RT textures (no packet guest bytes).
- Render and sampler states including per-sampler filter/mipfilter/addressing/sRGB values and their ordered final values; viewport six DWORDs; color RT and depth surface guest identity and complete eight DWORD `D3DSURFACE_DESC` (Format, Type, Usage, Pool, MultiSampleType, MultiSampleQuality, Width, Height).
- `last_clear_flags,color,depth_bits,stencil,rect_count` **plus** a target identity and ordering witness for the clear, because last-clear parameters alone do not prove a clear of the currently bound target. Or supply an ordered preceding frame trace/current attachment contents. Existing P2 builder explicitly rejects synthetic clear with unproven target.
- Explicit evidence that the P1 callback was **invoked**, returned success, bundle admission succeeded, and Vulkan submitted a draw under validation; ideally output readback hash and comparison with captured retail target if parity is claimed. Host-frame/guest-dispatch counts never replace this.

### Fail-closed limitations

- Active DXT3 sampler data must be available in a P1 packet; merely creating or locking a DXT3 resource does not establish a sampled DIP.
- Existing capture-bundle supports pixel `sampler2D` s0–s15 and only supported pipeline/RT formats; vertex-texture samplers or unsupported states are separate gates. Multi-level DXT3 with active mip filtering remains blocked until native mip-chain transport/upload is implemented.
- `D3DFMT_DXT3` and `VK_FORMAT_BC2_*` are not conflated: the current selected approach is **CPU BC2 decode, then RGBA8 native upload**. Direct BC2-native upload would require device feature checks, new packet format/record compatibility, copy alignment and level handling; it is not the minimum path for the supplied one-level evidence.
- A successful `SVTP/1` build from synthetic DXT3 blocks is **not** original payload proof, in-process retail draw proof, native GPU upload proof, or image parity.

## Exactly next actions

1. **P2:** Review PR #2144's successful CI run and BC2 four-color regression. Keep PR #2143 unchanged; preserve it as the independent guest managed-capture capability.
2. **P1 → P2 boundary:** Capture one *actual* synchronous DIP packet with DXT3 bound to a shader-used pixel sampler and with full, current buffer/shader/state/mip evidence. Preserve the exact raw mip payload hash and the callback sequence.
3. **P2 after positive packet:** Import the packet DDS as `DXT3`, verify identity and raw payload, transcode `RGBA8`, construct the SVTP/1 bundle, then perform native Vulkan 1.1 validation/submission. Only then claim **DXT3 resource-and-draw execution**; assess retail image parity separately.

### Source locations checked

- [P1 packet and capability PR #2143](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2143)
- [P2 graphics correction PR #2144](https://github.com/Hanz0Hatt0r1/nfs-shift-decompilation/pull/2144)
- `native_vulkan/src/d3d9_packet_capture_adapter.cpp` (`dds_bytes`, `install`)
- `src/render/texture_reference.py` (`_decode_dxt1_block`, `_decode_dxt3_block`, `_decode_dxt5_block`, `decode_dds`)
- `src/render/vulkan/vulkan_d3d9_capture_bundle.py` (`_capture_texture_packet`, clear/constant gates)
- `src/render/vulkan/vulkan_texture_packet.py` (SVTP/1 RGBA8 serialization)
- `native_vulkan/src/vulkan_texture_sampler.hpp`, `native_vulkan/src/vulkan_bundle_execute.cpp` (Vulkan RGBA8 UNORM/SRGB consumer)
- `tests/test_texture_reference.py`, `tests/test_vulkan_d3d9_capture_bundle.py` (P2 regressions)
