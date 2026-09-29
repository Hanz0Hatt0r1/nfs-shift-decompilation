# Phase 529 — BMW primitive material-slice set

Phase 529 joins multiple independently validated Phase 528 BMW primitive
material slices into one canonical multi-submesh RenderCommand.

## Input contract

Each input must be a ready `SHIFT.BMWMaterialSlice/1` with:

- a ready generic material gate;
- a ready slice golden gate;
- exactly one ready RenderCommand submesh;
- the canonical BMW body LODA resource identity and SHA-256;
- a neutral mesh payload derived from that same resource.

Primitive indices must be unique. Inputs are reordered by primitive index so
the resulting draw list follows canonical MEB primitive order rather than file
or CLI argument order.

## Cross-slice equality gates

All slices must agree on:

- exact MEB resource path;
- exact MEB SHA-256;
- neutral mesh content hash;
- RenderCommand mesh content hash;
- world matrix content hash.

Texture-source provenance is unioned by normalized path. Reusing the same path
with different SHA-256 values blocks the set.

## Output

`SHIFT.BMWMaterialSliceSet/1` contains:

- the ordered primitive/material list;
- one combined `SHIFT.RenderCommand/1`;
- the shared neutral mesh;
- unioned DDS source provenance;
- a stable set identity hash.

The combined command is revalidated with the normal RenderCommand validator;
single-slice command metadata is not reused as an aggregate identity.

## Native handoff

The Phase 527 `build_bmw_vulkan_set_from_material_slice()` adapter accepts the
Phase 529 set directly. Each combined submesh is still split back into its own
atomic Vulkan bundle, retaining per-draw shader, constants, DDS bridge and
provenance before Phase 525 preparation and Phase 526 native execution.

This closes the structural path for real PAINT + non-paint BMW draws. Actual
non-paint admission remains dependent on Phase 528 resolving each retail
material to a unique exact shader permutation.
