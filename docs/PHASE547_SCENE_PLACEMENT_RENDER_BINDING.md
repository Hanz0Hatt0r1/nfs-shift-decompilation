# Phase 547 — neutral SGB scene placement to RenderBinding

Phase 547 closes the last FLAT spatial payload needed by the Phase 545
placement identity join and exposes the result as a neutral scene-placement
contract.

## FLAT leaf +0x20..+0x34

Phase 546 intentionally kept these six floats below the source-proof threshold.
The retail call site now closes that gap.

`FUN_006afb20` passes the direct FLAT record to `FUN_006aef20`. When the
query object has its secondary spatial interface, `FUN_006aef20` calls the
query object's vtable `+0x2c` with:

```text
leaf + 0x20
query + 0x20
```

The six-float payload is therefore directly consumed by the spatial query.

The Silverstone Era3 corpus independently validates its AABB-shaped layout:
all 21,580 leaves contain ordered `min_xyz/max_xyz` triples; every
source-backed sphere center lies inside those bounds; and the min/max midpoint
matches the sphere center within a maximum absolute error of
`6.103515625e-05`.

The IR now exposes `spatial_bounds` as
`source-consumed-corpus-validated-aabb`.

## Complete neutral FLAT placement payload

A FLAT/SUMM placement can now carry, without guessing:

- tree-node AABB;
- 64-bit include mask;
- 64-bit exclude mask;
- bounding sphere center/radius;
- six-float leaf spatial bounds;
- exact FLAT runtime index;
- exact SUMM wrapper identity/resource.

Individual filter-mask bit meanings remain unresolved.

## PART/NODE precision

The alternate PART/NODE path carries source-backed partition AABB plus exact
one-based NODE wrapper identity. It is marked `partition` precision rather
than inventing a per-object sphere or leaf bounds.

## SHIFT.ScenePlacement/1

`src/scene/scene_placement.py` converts
`SHIFT.SGBPlacementJoin/1` into `SHIFT.ScenePlacement/1`.

Each entry records:

- a stable placement id;
- placement mode;
- object/resource/kind identity;
- spatial precision;
- source-backed bounds/sphere/masks available for that mode;
- the source join that established the identity.

The contract fails closed when a required FLAT leaf spatial payload or PART
partition AABB is absent or invalid.

## RenderBinding handoff

`attach_scene_placement()` adds the ready placement contract as the top-level
`scene_placement` member of `SHIFT.RenderBinding/1`.

It deliberately does not mutate or regenerate:

- DrawPacket entries;
- StaticDraw entries;
- RenderCommand entries;
- world matrices.

This is a neutral scene/culling data handoff, not an invented transform bridge.

## CLI

```bash
python shift_importer.py sgb-runtime track.sgb out/sgb-runtime.json
python shift_importer.py sgb-placement-join \
  out/sgb-runtime.json out/sgb-placement-join.json
python shift_importer.py sgb-scene-placement \
  out/sgb-placement-join.json out/scene-placement.json
python shift_importer.py attach-scene-placement \
  render-binding.json out/scene-placement.json out/render-with-placement.json
```

## Boundary

The scene-to-render neutral placement boundary is now explicit. Remaining scene
work can focus on higher-level streaming/LOD behavior rather than assigning
semantics to bytes solely to unblock rendering.
