# Race-window texture snapshot identities — 2026-10-18

This report hashes the existing user-confirmed PortProton race capture's
texture snapshot files and joins their paths to target-shader sampler binds.
It does not run the game or require another capture.

## Result

- The source JSONL has SHA-256
  `d90ede38815242dc4a7ff5771b9d886e26931590621631f16ea4617852276afe` and
  contains 202,870 valid events from trigger windows 5865–5869 and 6983–6987.
- All **813 / 813** target draws have exact capture-local shader, geometry,
  reflected constants, and sampler state; all 813 observed explicit sampler
  state writes.
- The target draws contain **3,055 sampler bindings**. **945** bindings from
  **331 draws** directly reference a captured snapshot, across **85 files**.
- The analyzer hashed all **541** snapshot files present in the capture bundle;
  none were missing. Snapshot paths use pointer-based filenames, so the hashes
  identify the file bytes present at analysis time, not every historical bind.
- A snapshot was observed on the same texture generation for **1,353** other
  target bindings. Those remain candidates because content stability between
  binds is unproven. **27** bindings have multiple candidates and **730** have
  no same-generation snapshot candidate.
- No event supplies the original retail `resource_path` plus
  `resource_sha256`. Capture-local snapshot hashes do not establish the
  original game asset path, BMT/material identity, or Vulkan render admission.

The full derived sampler report is stored as
[`d3d9_race_target_texture_sampler_20261018.json.gz`](../evidence/retail_frontier_20261018/d3d9_race_target_texture_sampler_20261018.json.gz).
Its SHA-256 is
`ec9403edcd635242dfee1220952a8ec384d301f7bf5c0be1d4f8a3cd83fde1c7`.
The raw JSONL and texture payloads remain outside Git under
`/home/pes/nfs-shift-recompilation-artifacts/portproton-retail-capture-20261018/retail-race-after-load-20261018/`.

## Reproduce

```bash
python3 src/graphics/d3d9/d3d9_target_texture_sampler_evidence.py \
  /home/pes/nfs-shift-recompilation-artifacts/portproton-retail-capture-20261018/retail-race-after-load-20261018/shift_d3d9_capture.jsonl \
  /tmp/d3d9_race_target_texture_sampler_20261018.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json \
  --snapshot-root /home/pes/nfs-shift-recompilation-artifacts/portproton-retail-capture-20261018/retail-race-after-load-20261018/textures

gzip -n -9 -c /tmp/d3d9_race_target_texture_sampler_20261018.json \
  > evidence/retail_frontier_20261018/d3d9_race_target_texture_sampler_20261018.json.gz
```

The next renderer-evidence step is to hash and associate the captured VB/IB
payloads with draw buffer generations, then compare them with static IMB
resources. No draw is admitted to the Vulkan translator by this report.
