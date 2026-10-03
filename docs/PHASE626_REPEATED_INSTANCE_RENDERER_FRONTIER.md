# Phase 626 — repeated-instance renderer frontier

Phase 626 folds `SHIFT.IMBRepeatedSceneInstanceTransformJoin/1` back into the
central `SHIFT.D3D9RendererFrontierAudit/1`.

This is a frontier/accounting stage. It does not add a new observation source.
It decides what remains after Phases 623–625 have progressively narrowed:

```text
static geometry candidates
→ exact source-backed SGB/LOD references
→ exact same-event runtime IMB resource identity
→ exact repeated scene instance by draw-local float32 transform
```

## New frontier input

`d3d9_renderer_frontier_audit.py` accepts:

```text
--repeated-instance-transforms <SHIFT.IMBRepeatedSceneInstanceTransformJoin/1>
```

The report summary records `phase625_applied=true` and source provenance retains
the exact input format.

## Exact closure

`scene_resource_exact_draw_attribution` becomes `closed-offline-exact` when:

- Phase 625 reports `ready=true`;
- `remaining_scene_draw_ambiguity_count == 0`.

Confidence is:

- `exact-same-draw-f32-world-matrix-instance-evidence`.

This closure does not erase historical capture absences. In particular,
`vb_ib_payload_equality` remains `absent-in-capture` when the historical capture
contains no buffer payload. The important distinction is that buffer bytes are
not needed to resolve repeated placements of the same exact mesh.

## Remaining blocker classes

### Incomplete scene world matrices

When any repeated candidate lacks a complete source-backed numeric world matrix,
the frontier directs work to world-matrix materialization/root consensus.

A missing matrix is not a contradiction, so a different candidate cannot win by
default.

### Equal or multiple exact matrix matches

If two placements have the same exact observed transform, transform evidence
cannot select one. The next offline discriminator is source-backed placement
spatial/partition/visibility evidence.

VB/IB payload is explicitly rejected as a discriminator here because the
placements already share the same exact IMB resource and world matrix.

### Missing draw-local transform observation

The frontier first directs work back through the existing raw/draw-local D3D9
constant state for the exact Phase 624 event. This is not promoted to a capture
request merely because one intermediate pipeline report lacks the observation.

### Upstream non-instance ambiguity

Phase 625 only processes repeated placements. Any Phase 624 conflict or
non-instance resource/scene blocker remains visible and must be resolved by its
own exact provenance chain.

## Policy additions

The central frontier records:

- `exact_f32_world_matrix_is_instance_witness=true`;
- `incomplete_world_matrix_is_contradiction=false`;
- `equal_world_matrices_select_instance=false`;
- `buffer_payload_relevant_to_repeated_instance=false`.

These are proof boundaries, not ranking preferences.

## Regression coverage

`tests/test_d3d9_renderer_frontier_audit.py` covers:

- full Phase 625 closure;
- preservation of historical buffer-payload absence after closure;
- incomplete-world-matrix continuation;
- equal-transform continuation to spatial evidence;
- missing-transform-observation fallback to existing draw-local constants;
- preservation of Phase 624 non-instance ambiguity;
- empty Phase 625 input not overwriting an earlier exact closure;
- fail-closed input format validation.
