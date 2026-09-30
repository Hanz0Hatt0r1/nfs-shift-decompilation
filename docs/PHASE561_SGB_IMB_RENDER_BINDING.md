# Phase 561 — admitted IMB → generic RenderBinding

Phase 561 connects the Phase 560 neutral IMB geometry contract to the existing
scene/render pipeline.

The scene path now supports both:

`admitted SGB OBJECT → MEB → RenderBinding`

and:

`admitted SGB OBJECT → MeshInst/.imb → SHIFT.IMBNeutralGeometry/1 → RenderBinding`.

## Resource resolution

`build_render_bindings_from_resource_instances()` now accepts resolved
`.imb` resources in addition to `.meb`.

For IMB it:

1. loads the raw payload recorded by the IR manifest;
2. runs the source-backed v0.4 neutral adapter;
3. rejects decode or geometry-readiness failures explicitly;
4. reuses the existing BMT/MTX → FX/FXO → material binding path;
5. builds the same DrawPacket/StaticDraw/RenderCommand contracts used by MEB.

No IMB JSON is required in the manifest. The raw payload remains the authority.

## Provenance

IMB is not relabeled as MEB.

The generated packet records:

- `mesh.source_kind = "IMB"`;
- `mesh.neutral_adapter_format = "SHIFT.IMBNeutralGeometry/1"`;
- `vertex_layout.source = "IMB"`;
- the exact manifest path/archive/SHA provenance.

MEB continues to report `source_kind = "MEB"`.

## Fail-closed behavior

An admitted `.imb` row is still blocked when:

- the resource is absent from the analyzed IR;
- the raw IMB cannot be decoded;
- the neutral geometry adapter reports a blocker;
- downstream material/shader/resource resolution fails.

The existing RenderBinding material and shader gates remain unchanged.

`.imx` stays explicitly blocked pending an XML neutral adapter.

## SGB bridge

`SHIFT.SGBRenderBindingBridge/1` now sends both `.meb` and `.imb`
instances to the generic render pipeline. Other MeshType resources and
`.imx` remain in the adapter-blocked set.

This removes the binary MeshInst adapter blocker from the first native
Silverstone vertical slice.

## Next

The next scene milestones are:

- validate this path against real Silverstone IMB resources from the corpus;
- implement the IMX XML neutral adapter;
- feed admitted scene geometry directly into native runtime loading;
- independently close per-instance SceneGraph transform update history.
