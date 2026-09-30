# Phase 560 — neutral IMB geometry adapter

Phase 560 turns the source-backed v0.4 IMB payload recovered in Phases 557–559
into a renderer-neutral geometry contract.

The new adapter is:

`src/scene/imb_neutral_geometry.py`

and emits:

`SHIFT.IMBNeutralGeometry/1`.

## Input boundary

The adapter deliberately reuses `parse_imb_binary_mesh(..., decode_primitives=True)`.
It therefore accepts only the already-proven v0.4 path:

`prefix → fixed header → optional bones → descriptor/vertex blocks → primitive records`.

No new binary-layout guesses are introduced in this phase.

## Neutral field mapping

Serialized stream identity remains the exact retail
`[Type ordinal, Usage ordinal, Channel]` triple.

Only triples already established elsewhere in the repository are promoted to
neutral fields:

- `200` → position;
- `220` → normal;
- `240` → tangent;
- `250` → second tangent/binormal-shaped field;
- `130..134` → float2 UV layers;
- `230..234` → float3 UVW layers;
- `310` → four-float bone weights;
- `460/461` → packed four-byte colors;
- `580` → four-byte bone indices.

Any other source-backed stream is retained byte-for-byte in
`deferred_streams`. The adapter does not invent a semantic label.

## Primitive normalization

Each decoded IMB primitive is converted into an ordered neutral draw range:

- material resource name;
- first index in the combined neutral index array;
- index count / triangle count;
- source vertex range;
- optional bone palette;
- source-backed sphere and AABB;
- source offsets/sizes for provenance.

Per-primitive bone palettes remain local to their primitive. Phase 560 does not
invent a palette remap into global bone indices.

## Important non-equivalence

The output mesh uses `SHIFT.NeutralMesh/1`, not `SHIFT.MEB`.

IMB and MEB now share a neutral geometry vocabulary, but their serialized
containers, material ownership and runtime resource paths remain distinct.

## Readiness

A geometry report is ready when the proven POSITION0 stream is present and the
decoded primitive payload is internally consistent.

Unknown extra streams are not blockers because they remain preserved as raw
deferred evidence. Material/shader resolution and RenderCommand construction
are intentionally outside this adapter.

## CLI

The module can be used directly:

```bash
python src/scene/imb_neutral_geometry.py \
  extracted_mesh.imb \
  out/mesh-neutral.json
```

## Next

The next scene integration step is to teach
`SHIFT.SGBRenderBindingBridge/1` to resolve admitted `.imb` resources into
this neutral geometry contract and then add a MeshInst-specific material/draw
binding layer without pretending the resource is MEB.
