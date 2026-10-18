# Retail D3D9 capture audit — 2026-10-18

The existing PortProton capture provides a useful target for the next renderer
vertical slice. The raw capture is **496,679,972 bytes** and remains in the
installed game directory; this repository stores its hash and derived reports,
not another copy of the 474 MiB JSONL file.

## Source and provenance

- Game: `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`
- Capture proxy beside the game: `d3d9.dll`, SHA-256 `0316e6b7e799964fb63bd367e96a99d367c42b5edf55aa6789040d53038c0b7f`
- Raw JSONL: `/home/pes/PortProton/data/prefixes/DEFAULT/drive_c/GOG Games/Need For Speed.Shift.v 1.02/shift_d3d9_capture.jsonl`
- Raw JSONL SHA-256: `d3f3076228258eb4c72983dd5d0ea00f3c13af0c39c1a837f81c2371c5b7dcdc`
- Capture file modification time: 2026-10-02 07:35:51 +0300
- Exact source path, byte size, executable/proxy hashes, and derived report hashes: [provenance JSON](../evidence/shift_d3d9_capture_provenance_20261018.json)

The capture covers 4,309 frames over 308,332 ms and contains 1,718,778 valid
JSON objects. It has 252 unique vertex-shader hashes, 457 pixel-shader hashes,
201,533 indexed draws, 5,162 index-buffer creations, and 3,509 vertex-buffer
creations.

## Target draw evidence

Against `evidence/silverstone_era3_runtime_shader_targets.json`, 19 of 51 target
pixel-shader hashes were created and 9 hashes were bound for **1,581 draws**
between frames 4287 and 4308. The strongest crowd-generation candidate is:

- Pixel shader SHA-256: `d7859ccad24d2884b4e4eebeb2f520ea6fcdfbbd65cdc475c22f86a4200d351a`
- Existing capture hits: 537
- D3D9 resource-trigger signature: `ps:b83e3c4ec719e80f`

The reusable audit now derives the proxy's FNV-1a trigger signature from the
captured shader bytes and reports it alongside the shader SHA-256. The compact
target report groups 55 buffer/range geometry identities, distinguishes 374
instance-stream identities, and observes 38 texture identities. The full
per-draw report is stored as gzip at
`evidence/shift_silverstone_target_draw_local_20261018.json.gz`; decompress it
with `gzip -dc` for all draw-local constants and bindings.

This is capture-local evidence only. The capture contains no VB/IB payloads,
texture snapshots, or exact resource path/SHA pairs, so the target draws are not
yet suitable for retail resource admission or Vulkan rendering. The detail
extractor flags 16,229 malformed constant-write events; those writes need their
own audit before constant signatures are treated as complete. Repeated JSON
keys occur on 2,912 lines, but the auditor found zero lines where repeated
values conflict. Duplicate keys still make the source JSON ambiguous to generic
readers and should be removed in future producer output.

## Reproduce the reports

From the repository root:

```bash
python3 src/graphics/d3d9/d3d9_raw_capture_audit.py \
  '/home/pes/PortProton/data/prefixes/DEFAULT/drive_c/GOG Games/Need For Speed.Shift.v 1.02/shift_d3d9_capture.jsonl' \
  evidence/shift_d3d9_capture_audit_20261018.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json

python3 src/graphics/d3d9/d3d9_target_draw_local_evidence.py \
  '/home/pes/PortProton/data/prefixes/DEFAULT/drive_c/GOG Games/Need For Speed.Shift.v 1.02/shift_d3d9_capture.jsonl' \
  evidence/shift_silverstone_target_draw_local_summary_20261018.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json \
  --compact-summary

python3 src/graphics/d3d9/d3d9_target_draw_local_evidence.py \
  '/home/pes/PortProton/data/prefixes/DEFAULT/drive_c/GOG Games/Need For Speed.Shift.v 1.02/shift_d3d9_capture.jsonl' \
  /tmp/shift_silverstone_target_draw_local_20261018.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json

gzip -n -9 -c /tmp/shift_silverstone_target_draw_local_20261018.json \
  > evidence/shift_silverstone_target_draw_local_20261018.json.gz
```

For the next focused PortProton run, use the trigger signature above and enable
VB/IB payloads plus texture snapshots into new persistent output directories.
The producer now bounds its pre-trigger buffer cache to 256 MiB by default and
records retained/evicted/oversized totals when the trigger fires. Keep the
capture in an external artifact directory; do not replace the existing game
proxy or source JSONL.

The Linux lowered-code/Vulkan smoke remains separate from this capture: it
renders converted synthetic MGEO geometry and does not yet consume these retail
D3D9 draws.
