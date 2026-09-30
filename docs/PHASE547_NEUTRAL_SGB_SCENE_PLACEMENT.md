# Phase 547 — neutral SGB scene placement

Phase 547 turns the Phase 545 placement identity joins and Phase 546 FLAT query
geometry into a single render-facing, fail-closed placement contract:

`SHIFT.SGBScenePlacement/1`.

It deliberately stops before draw admission.

## FLAT / SUMM placements

Every ready FLAT/SUMM link preserves:

- FLAT `runtime_index` and matching SUMM source order;
- SUMM wrapper/object identity;
- source-backed FLAT tree-node AABB;
- source-backed include/exclude filter-mask pairs;
- source-backed direct-record bounding sphere.

The six floats at FLAT leaf `+0x20..+0x34` are carried only as an
`advisory-only` bounds candidate. They are never placed in
`proven_geometry` and are explicitly marked
`used_as_proven_aabb=false`.

## PART / NODE placements

The alternate PART/NODE mode preserves:

- PART record and partition identity;
- one-based source child-object ID;
- zero-based NODE wrapper-registry index;
- NODE wrapper/object identity;
- source-backed PART partition AABB.

No FLAT leaf filter mask or bounding sphere is invented for this path.

## RenderBinding boundary

Every placement includes a `render_binding_handoff` section with the resource
reference and object kind. The contract intentionally reports:

```text
world_transform_status = not-emitted
draw_admission = false
```

A placement can therefore be structurally ready without becoming a render draw.

Before draw admission the next adapter must still prove:

1. the object/resource-to-render-node mapping;
2. a source-backed world transform, or an explicit identity-transform case.

This keeps spatial culling evidence separate from transform/render semantics.

## CLI

```bash
python shift_importer.py sgb-runtime track.sgb out/sgb-runtime.json
python shift_importer.py sgb-placement-join \
  out/sgb-runtime.json out/placement-join.json
python shift_importer.py sgb-scene-placement \
  out/placement-join.json out/scene-placement.json
```

## Production boundary

For Silverstone Era3, Phase 545 already proves the FLAT/SUMM identity join over
21,580 placements and Phase 546 proves the mask/sphere/node-AABB layout used by
this contract.

Phase 547 does not add a new semantic claim to the unresolved leaf
`+0x20..+0x34` block and does not flatten LOD/HIERARCHY transforms without a
separate proof.
