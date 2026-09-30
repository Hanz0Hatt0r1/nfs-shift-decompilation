# Phase 546 — FLAT spatial and filter payload

Phase 546 closes the FLAT fields required to carry source-backed spatial
placement into the next neutral scene layer while keeping one still-unresolved
six-float block explicitly below the source-proof threshold.

## Source-backed direct-record fields

Retail query paths `FUN_006aef20/FUN_006aefe0` prove that every 0x40-byte
direct record contains two 64-bit filter domains:

- `+0x00/+0x04`: include mask pair;
- `+0x08/+0x0c`: exclude mask pair.

The query accepts an include domain when the requested include pair is absent or
has any overlap with the leaf pair. The exclusion domain accepts when the
requested exclude pair is absent or has no overlap with the leaf pair.

The same functions consume:

- `+0x10/+0x14/+0x18`: bounding-sphere centre XYZ;
- `+0x1c`: bounding-sphere radius.

The plane test is equivalent to
`dot(plane.xyz, centre) + plane.w + radius >= 0`.

## Source-backed tree-node AABB

The first six dwords of each 0x20-byte FLAT tree header are exposed as
`aabbox.min_xyz/max_xyz`.

`FUN_00689db0` provides the producer-side join: when PART runtime geometry is
materialized into FLAT form, PART node bounds at runtime `+0x04..+0x18` are
copied to generated FLAT header `+0x00..+0x14`.

## Leaf +0x20..+0x34 remains source-unresolved

These six floats are deliberately **not** named as a source-proven AABB.

The four-variant Silverstone Era3 corpus nevertheless gives a very strong
candidate invariant over all 21,580 direct records:

- all three candidate min components are <= their matching max components;
- the source-backed sphere centre lies inside the candidate bounds;
- the candidate min/max midpoint equals the sphere centre within 1e-4;
- maximum observed midpoint error is 6.103515625e-05.

The IR exposes this as `spatial_bounds_candidate` with
`source_consumer_proven=false` and keeps the raw `+0x20..+0x34` words.

## Retail corpus

`evidence/silverstone_era3_flat_spatial_observation.json` records the four
Silverstone Era3 SGB identities and aggregate invariants. Across the same
21,580 direct records:

- no serialized include/exclude mask word is non-zero;
- no serialized `+0x38` direct-object pointer is non-zero.

Those zeroes are corpus observations, not universal format defaults.

## Boundary

Phase 546 is sufficient to represent the proven FLAT query/filter geometry
without inventing the remaining six-float semantics.

The next scene step is to build a neutral placement contract from the Phase 545
object identity join plus Phase 546 node AABB, filter masks and bounding sphere,
then feed that contract toward RenderBinding.
