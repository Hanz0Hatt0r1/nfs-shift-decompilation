# D3D9 DXT snapshot probe — 2026-10-18

The capture proxy now writes managed and system-memory DXT1/2/3/4/5 textures
directly to legacy DDS files. It copies compressed blocks for every mip level,
preserving the original texture data instead of decoding it through the PPM
readback path.

## Verification

- The 32-bit MinGW `shift_d3d9_capture` target linked successfully.
- The focused capture and raw-audit regressions passed.
- The built proxy SHA-256 is
  `dc3aac598531b465299408e5b3b18f3a0ff154c0c8e671f8f0e540b685ed3a3c`.
- A PortProton run from an isolated copy of retail `SHIFT.exe` produced
  495 captured texture-snapshot events and 610 VB/IB payload events. The raw
  JSONL SHA-256 is
  `5b7f50403868c371c9a0d5c2e486080631ec0e076414075a74e59c508979edb0`.
- The 11 unique DDS paths referenced by that capture all had valid headers and
  payload lengths. They contain DXT5 blocks with one to eleven mip levels.
- The capture audit parsed 30,984 JSON objects without malformed lines or
  duplicate keys. It found no match for the 51 supplied target pixel-shader
  hashes and no `resource_path`/`resource_sha256` identity events.

## Runtime boundary

The captured process still had `Movies/Attract.bik` open at the final trigger
window. These D3D9 snapshots therefore establish that compressed textures can
be captured, but they do not establish frontend interaction, race rendering,
or a usable Vulkan resource mapping. The snapshot filenames remain
pointer-based and are reused if the same texture is bound again; this probe
retains only the latest bytes at each referenced path.

No raw game capture or proprietary texture payload is stored in Git. Machine
readable counts, hashes, and limitations are recorded in
[`../evidence/retail_frontier_20261018/d3d9_dxt_snapshot_probe.json`](../evidence/retail_frontier_20261018/d3d9_dxt_snapshot_probe.json).
