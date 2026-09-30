# Phase 553 — SGB admitted resource → generic RenderBinding bridge

Phase 553 closes the non-capture branch left by Phase 552.

The scene path is now:

```text
SHIFT.SGBScenePlacement/1
        +
SHIFT.SGBObjectRenderHandoffSet/1
        ↓
SHIFT.SGBRenderBindingAdmission/1
        ↓ admitted rows only
SHIFT.SGBRenderBindingBridge/1
        ↓
SHIFT.RenderBinding/1
```

## What is joined

Each scene-admitted row already contains:

- source-backed placement identity and spatial-culling readiness;
- the exact OBJECT resource reference;
- a numeric 4x4 world matrix.

The new bridge preserves that world matrix byte-for-value at the numeric
contract level and resolves the resource reference through the existing
resource IR.

The generic render pipeline now has a second entry point,
`build_render_bindings_from_resource_instances()`, which accepts externally
placed MEB instances without requiring a synthetic VHF node.

## Fail-closed resource policy

Phase 553 does not infer a higher-level resource type from an OBJECT string.

A scene resource is promoted only when the IR manifest resolves it to a
`.meb` entry. Missing resources and currently unsupported non-MEB resources
remain explicit blockers.

Once the MEB resolves, existing behavior is reused for:

`MEB → BMT/MTX → FX/FXO → DrawPacket → StaticDraw → RenderCommand`.

Shader ambiguity, missing material state or renderer-resource blockers remain
owned by those existing contracts. Phase 553 does not convert a scene-ready
object into a draw-ready command by assertion.

## Partial scenes

Blocked Phase 552 rows are never promoted. Ready rows can still enter the
generic resource pipeline independently, so one MatrixNumber instance with
unknown SceneGraph update history does not erase unrelated explicit-transform
objects.

`SHIFT.SGBRenderBindingBridge/1` reports:

- scene-admitted instance count;
- resolved/unresolved instance counts;
- skipped scene bindings;
- the complete embedded `SHIFT.RenderBinding/1` result.

## CLI

```bash
python shift_importer.py sgb-render-binding-bridge \
  out/scene-render-admission.json \
  out/ir \
  out/scene-render-binding.json
```

The IR root is an existing analyzed resource tree containing
`manifest.json` and decoded MEB/BMT/FX resources.

## Boundary

Phase 553 closes admitted SGB resource integration with the generic
RenderBinding pipeline for MEB resources.

The main scene evidence blocker is now narrower: MatrixNumber-backed instances
whose per-instance SceneGraph transform-update history is unknown remain
blocked before this bridge. Higher-level streaming/LOD behavior and native
scene visibility scheduling also remain separate runtime questions.
