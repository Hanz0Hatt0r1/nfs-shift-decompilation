# Phase 576 — exact IMB runtime shader → scene render bridge

Phase 575 can rebuild one complete `SHIFT.MaterialBinding/1` from a
runtime-proven shader admission. Phase 576 joins that admission back to the
exact IMB primitive inside the existing SGB scene/render path.

## Integration point

The existing resource-instance render pipeline now accepts:

`runtime_shader_admission: SHIFT.IMBRuntimeShaderAdmission/1`

through:

`build_render_bindings_from_resource_instances(...)`.

`SHIFT.SGBRenderBindingBridge/1` forwards the same optional report.

No parallel renderer or scene representation is introduced.

## Exact join key

A Phase 574 admission is eligible for one IMB primitive only when all static
identity fields agree:

- archive;
- IMB resource path;
- decoded IMB SHA-256;
- primitive index;
- source `first_index/index_count/primitive_count`;
- source material reference;
- resolved BMT path;
- resolved BMT SHA-256 when present in the admission;
- shader source path.

The selected admission is then passed to Phase 575
`material_linker.link_material(..., runtime_admission=...)`.

MEB resources never receive IMB runtime shader admissions.

## Resource-level admission, scene-level reuse

Runtime shader attribution is a property of the IMB resource primitive, not one
particular SceneGraph placement.

The same admitted resource primitive may therefore be used by several scene
instances. Phase 576 tracks:

- unique admitted bindings applied;
- total scene-instance applications;
- per-binding application counts.

A single proven binding can legitimately have `application_count > 1`.

## Fail-closed behavior

When a runtime shader admission report is supplied, the bridge blocks if:

- the report contains no admitted bindings;
- an admitted binding does not map to any scene/render primitive;
- more than one admission row targets the same exact resource primitive;
- source draw range differs;
- material/BMT/shader identity differs;
- Phase 575 material relinking rejects the admission.

The pipeline does not silently fall back to static ranking for an admission that
claims to target the current primitive.

Primitives with no matching admission continue through the existing static
material path. This permits partial capture evidence while keeping proven and
unproven primitives distinct.

## Output contract

`SHIFT.RenderBinding/1` now includes:

`runtime_shader_join: SHIFT.IMBRuntimeRenderBindingJoin/1`.

Each submesh also records its exact runtime admission, when applied.

`SHIFT.SGBRenderBindingBridge/1` exposes the same join and promotes join
blockers into bridge blockers when a runtime admission report was explicitly
supplied.

## CLI

The existing command now supports:

```bash
python shift_importer.py sgb-render-binding-bridge \
  out/scene-render-admission.json \
  out/ir \
  out/scene-render-binding.json \
  --runtime-shader-admission out/runtime-shader-admission.json
```

The standalone `sgb_render_binding_bridge.py` CLI exposes the same optional
argument.

## Regression coverage

Phase 576 covers:

- exact IMB primitive admission application;
- wrong resource SHA remaining blocked;
- MEB exclusion;
- one resource-level admission reused by multiple scene instances;
- empty runtime admission report remaining blocked;
- CLI option parsing.

The ordinary VHF render path does not consume the runtime-admission contract.

## Next

With an authentic Silverstone runtime capture, the complete path is now:

`capture → target match → shader admission → exact scene primitive
→ MaterialBinding → StaticDraw → RenderCommand`.

The next code step is to freeze successful runtime-proven RenderCommands into a
compact Silverstone native-scene bundle and feed those commands to
`native_runtime`, while keeping unproven primitives fail-closed.
