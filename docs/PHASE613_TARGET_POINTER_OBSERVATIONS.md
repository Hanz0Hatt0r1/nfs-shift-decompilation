# Phase 613 — target resource pointer observations

## Purpose

Phase 612/611 can now produce static content candidates for every one of the 39
observed target resource shapes, but descriptor equality still leaves several
shapes ambiguous. The historical D3D9 capture already contains COM object
pointers for vertex buffers, index buffers and textures. Phase 613 preserves
that existing signal without changing the stable Phase 605 resource-shape
identity.

The new report format is:

`SHIFT.D3D9TargetPointerObservations/1`

## Stable shape alignment

The tool streams the raw JSONL capture and reconstructs the exact same
pointer-free resource-shape payload used by
`SHIFT.D3D9TargetDrawSignatureCatalog/1`:

- VS byte SHA-256;
- PS byte SHA-256;
- vertex declaration SHA-256;
- stream number/stride layout;
- index format;
- stream buffer descriptors;
- index-buffer descriptor;
- CTAB-filtered texture descriptors.

When `--target-catalog` is supplied, the observed resource-shape SHA set is
compared to the existing Phase 605 catalogue. `catalog_alignment.status=exact`
is required before pointer observations should be consumed downstream.

## Capture-local geometry pointer identity

For every target draw the report records:

- device pointer;
- stream-0 vertex-buffer pointer;
- vertex-buffer creation event index;
- index-buffer pointer;
- index-buffer creation event index;
- exact D3D9 draw range (`primitive_type`, `base_vertex_index`, `start_index`,
  `primitive_count`).

The dynamic stream-1 instance buffer is intentionally excluded from geometry
identity.

Including the creation event index prevents COM address reuse from conflating
two different runtime resource generations.

## Capture-local material pointer identity

For every target draw the report also records the texture pointers bound to the
same CTAB sampler registers used by Phase 605 resource-shape filtering. Each
texture entry includes its creation event index.

If CTAB reflection is unavailable, the same fallback rule as Phase 605 applies:
all currently bound texture stages are retained.

## Aggregation

Each stable resource shape exposes:

- `geometry_pointer_identity_count`;
- `material_pointer_identity_count`;
- `combined_pointer_identity_count`;
- full geometry/material/combined pointer observations with draw counts and
  frame ranges.

The summary also reports global unique pointer-identity counts and the number of
target draws with complete stream-0 VB + IB creation identity.

## Boundary

This evidence is strictly capture-local.

A pointer observation does **not** prove:

- retail archive path;
- IMB/DDS payload SHA-256;
- portable identity across runs;
- render admission.

Its purpose is to detect same-object relationships inside the already captured
session. A later candidate join may use those same-object links conservatively,
or conclude that a new payload capture is required.

## CLI

```bash
python src/graphics/d3d9/d3d9_target_pointer_observations.py \
  shift_d3d9_capture.jsonl \
  out/d3d9_target_pointer_observations.json \
  --target-inventory evidence/silverstone_era3_runtime_shader_targets.json \
  --target-catalog out/d3d9_target_draw_signatures.json
```

Expected validation for the current historical capture is an exact alignment
with the 39 Phase 605 resource shapes and 1581 target draws.
