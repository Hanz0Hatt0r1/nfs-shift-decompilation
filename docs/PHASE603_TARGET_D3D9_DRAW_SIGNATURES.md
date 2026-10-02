# Phase 603 — target D3D9 draw signatures

## Goal

Exploit the target-draw window already present in the production SHIFT capture
without requiring resource payloads or another game run.

Phase 602 reduces the supplied 201,533 indexed draws to 1,581 draws whose
currently bound pixel-shader byte hash belongs to the Silverstone Phase 568
target inventory. Only 9 target pixel hashes reach a draw, and their observed
frames are concentrated at the end of the capture.

`SHIFT.D3D9TargetDrawSignatureCatalog/1` clusters those target draws by
runtime-observable state.

## Pipeline signature

The pointer-free pipeline signature contains:

- vertex-shader SHA-256;
- target pixel-shader SHA-256;
- vertex-declaration payload SHA-256 when captured;
- active stream numbers and strides;
- active index-buffer format.

The signature intentionally excludes runtime pointer values.

## Resource-shape signature

A second signature adds descriptor shape, still without claiming identity:

- vertex-buffer length/usage/FVF/pool and stream stride;
- index-buffer length/usage/format/pool;
- bound texture stage, type, dimensions, format, levels, pool and usage.

Transient stream offsets are excluded from the stable resource-shape ID and
retained only as diagnostic observations. When pixel-shader CTAB reflection is
available, texture shape is restricted to sampler registers actually declared
by that shader; captures without usable CTAB retain all bound texture stages as
a conservative fallback. Two resources with the same descriptor shape may
still be unrelated. No resource hash or payload equivalence is inferred.

## Draw aggregation

Each signature records:

- draw count and summed primitive count;
- first/last frame;
- target shader families and target PS hashes;
- number of distinct observed draw ranges;
- up to eight representative draw-range/event samples.

This lets the next static/runtime correlation work on recurring render paths
instead of all raw D3D9 calls.

## Usage

```bash
python src/graphics/d3d9/d3d9_target_draw_signatures.py \
  shift_d3d9_capture.jsonl \
  out/d3d9_target_draw_signatures.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json
```

Relative input paths use the Phase 601 repository-root fallback.

## Evidence boundary

A pipeline/resource-shape signature is observational clustering only. It does
not prove an IMB path, primitive binding, material instance, scene instance or
same-instance shader attribution. Existing exact resource/draw/same-instance
gates remain authoritative.
