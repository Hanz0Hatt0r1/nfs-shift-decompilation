# Phase 602 — target shader draw coverage

## Goal

Extend the streaming raw D3D9 capture audit from target-hash presence to
observed draw usage without making resource or same-instance claims.

Phase 600 proved that a production capture can be classified cheaply. The
supplied Silverstone capture additionally contains 19 of the 51 Phase 568
pixel-shader hashes, so creation-only counts leave useful runtime evidence on
the table.

## Added observations

`SHIFT.D3D9RawCaptureAudit/1` now tracks pixel-shader state per D3D9 device:

- `CreatePixelShader` maps one runtime shader object to its SHA-256 byte hash;
- `SetPixelShader` updates the current shader for that device;
- `SetPixelShader(NULL)` clears it;
- each `DrawIndexedPrimitive` increments the currently bound target hash.

The report exposes:

- total target draw count;
- number of target hashes that reach at least one draw;
- first/last draw frame and draw count for each matched target hash;
- per-family target hash count, matched hash count, shader creation count and
  draw-hit coverage.

## Evidence boundary

Target draw coverage remains prefilter evidence only. A matching pixel shader
does not identify:

- one IMB resource;
- one primitive binding;
- one material instance;
- one scene instance;
- one exact VS/PS permutation.

Those claims remain behind the existing Phase 572+ resource/draw/same-instance
proof gates.

In particular, the compact checked-in Phase 568 production evidence retains
family/hash aggregates but not the complete per-binding target sets, so target
draw coverage must not be converted into a claimed number of covered primitive
bindings.

## Usage

The Phase 600 command is unchanged:

```bash
python src/graphics/d3d9/d3d9_raw_capture_audit.py \
  shift_d3d9_capture.jsonl \
  out/d3d9_capture_audit.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json
```

The resulting `target_inventory.family_coverage` and
`target_inventory.hash_observations` sections provide the new runtime
coverage.
