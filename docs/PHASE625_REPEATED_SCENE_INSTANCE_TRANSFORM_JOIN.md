# Phase 625 — repeated scene instance transform join

Phase 624 proves which exact IMB/LOD resource generated a captured draw. Its
remaining `exact-resource-draw-repeated-scene-instance` rows are not geometry
ambiguity: multiple SGB placements reference the same exact resource.

Phase 625 resolves only that residual instance-selection problem using evidence
already present in the project.

New contract:

- `SHIFT.IMBRepeatedSceneInstanceTransformJoin/1`

implemented by:

- `src/scene/imb_repeated_scene_instance_transform_join.py`

## Inputs

- `SHIFT.IMBRuntimeResourceDrawCandidateJoin/1` — Phase 624 exact same-draw
  resource identity;
- `SHIFT.SGBRuntimeObjectCandidateJoin/1` — complete source-backed candidate
  placements and their current numeric world matrices;
- `SHIFT.IMBRuntimeCapturePipeline/1` — draw-local captured vertex constant
  state for the already-attributed binding/frame/draw.

No original game execution and no new capture are required.

## Exact join key

The Phase 624 runtime witness is joined to captured constant state by:

```text
exact IMB resource_path + resource_sha256
+ binding_index
+ frame
+ draw_index
```

The resource identity is not reopened or re-ranked. Phase 625 only decides
which scene placement of the already-proven resource is compatible with the
same draw-local transform observation.

## Matrix observation contract

Phase 625 follows the existing Phase 591 observation policy:

1. collect every contiguous four-register window from the captured draw-local
   vertex constant state;
2. materialize each source-backed scene candidate world matrix as 16 floats;
3. compare IEEE-754 float32 bytes exactly;
4. test both row-major and transpose layouts;
5. do **not** assign a semantic name to the matching register window.

A candidate is never selected from approximate numeric equality.

## Complete-candidate requirement

A unique matching matrix is not enough if another surviving scene candidate has
no numeric world matrix. Missing transform data cannot be treated as a
contradiction.

Therefore every surviving scene candidate for the exact resource must have:

- `numeric_world_matrix_ready=true`;
- a complete finite 4x4 matrix.

Otherwise the row is
`blocked-incomplete-scene-world-matrices`.

## Resolution

A repeated instance becomes `exact-repeated-scene-instance` only when:

- the Phase 624 exact resource identity maps to a ready exact resource row in
  `SHIFT.SGBRuntimeObjectCandidateJoin/1`;
- at least two scene candidates are present, preserving the repeated-instance
  premise;
- every candidate has a complete source-backed world matrix;
- every relevant Phase 624 runtime witness has a matching draw-local constant
  observation;
- every observation matches exactly one scene candidate;
- all observations select the same scene candidate.

The selected output preserves placement identity, wrapper/source record,
object path, transform mode, matrix number, world matrix and exact register
witnesses.

## Ambiguity states

- `ambiguous-equal-or-multiple-world-matrix-matches` — more than one placement
  has a matrix found in the same captured constant state. Equal transforms do
  not select an instance.
- `blocked-incomplete-scene-world-matrices` — at least one surviving placement
  lacks a complete matrix.
- `draw-local-transform-observation-missing` — the exact resource/binding/frame/
  draw observation is absent from the existing pipeline.
- `repeated-scene-instance-unresolved` — complete evidence exists but does not
  yield one consistent placement.

Phase 624 non-instance blockers are carried forward as
`upstream_non_instance_ambiguity_count`; Phase 625 never pretends to solve them.

## Why VB/IB payload is irrelevant here

All repeated candidates in this stage already reference the same exact IMB
resource proven at the same raw draw. Vertex/index payload equality can only
re-prove the mesh; it cannot distinguish which placement of that mesh supplied
the world transform.

The correct discriminator is transform/spatial evidence, so
`buffer_payload_relevant_to_instance_selection=false` is explicit in the
contract.

## Regression coverage

`tests/test_imb_repeated_scene_instance_transform_join.py` covers:

- exact row-major float32 matrix selection;
- exact transpose selection;
- equal world matrices remaining ambiguous;
- incomplete candidate matrices preventing exclusion;
- wrong draw index not authenticating an instance;
- disagreement across same-draw witnesses;
- object-candidate coverage readiness;
- exact resource path+SHA lookup;
- preservation of upstream non-instance ambiguity;
- no-op behavior when Phase 624 already has a unique scene resource draw;
- input format validation.
