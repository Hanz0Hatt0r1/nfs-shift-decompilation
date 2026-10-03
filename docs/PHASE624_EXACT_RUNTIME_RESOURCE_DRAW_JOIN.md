# Phase 624 — exact runtime resource draw join

Phase 624 consumes already-existing runtime evidence to close the remaining
resource/LOD side of Phase 623 geometry ambiguity without requesting VB/IB
payloads.

New contract:

- `SHIFT.IMBRuntimeResourceDrawCandidateJoin/1`

implemented by:

- `src/scene/imb_runtime_resource_draw_candidate_join.py`

## Inputs

The stage joins:

- `SHIFT.IMBStaticSceneReferenceCandidateJoin/1` from Phase 623;
- `SHIFT.IMBRuntimeCapturePipeline/1` from the existing D3D9 attribution chain.

No original game execution is required. No new capture is required.

## Exact same-draw witness

A runtime resource observation is admissible only when all of the following are
already true in the capture pipeline:

1. the resource result has exact IMB `resource_path + resource_sha256`;
2. its `same_instance_gate.ready` is true;
3. the per-binding shader result is `attributed=true`;
4. the selected shader variant score is at least the existing strong threshold
   (`>= 80`);
5. the exact selected variant key occurs in one concrete runtime match;
6. that match preserves the raw D3D9 `draw.event_index`;
7. that event index equals the Phase 623 ambiguity row `event_index`;
8. the per-binding IMB path+SHA equals the resource container path+SHA;
9. the same path+SHA equals one Phase 623 candidate IMB identity.

The join does **not** use draw order, candidate rank, filename similarity, LOD
name patterns, frequency, or approximate draw-range similarity as proof.

## Why `event_index` matters

The runtime pipeline already stores the original raw D3D9 event index inside
`SHIFT.D3D9DrawStateSnapshot/1 -> draw.event_index`. Phase 624 therefore joins
resource attribution to the exact captured `DrawIndexedPrimitive`, not merely to
another draw in the same frame with compatible geometry metadata.

This closes a gap between:

```text
Phase 623 static candidate set
        +
source-backed SGB OBJECT/LOD reference
        +
existing same-instance D3D9 attribution
        +
exact raw draw event index
        ↓
exact IMB resource that produced this captured draw
```

## Resolution states

### `exact-scene-resource-draw`

One exact same-event runtime resource identifies one Phase 623 candidate, and
Phase 623 has exactly one source-backed SGB reference to that candidate.

This is sufficient to close the scene/resource identity of that draw.

### `exact-resource-draw-repeated-scene-instance`

The exact IMB resource is proven at the exact draw, but the same resource is
referenced by more than one SGB scene object.

This resolves geometry/LOD identity but **not** repeated-instance identity. The
next evidence gate is world transform/spatial instance selection. VB/IB payload
cannot distinguish two placements of the same exact mesh resource.

### `no-exact-runtime-resource-draw-witness`

The existing pipeline does not contain an admissible strong same-event witness
for that Phase 623 row. This is not itself a request for a new capture.

### `runtime-resource-not-in-phase623-candidate-set`

A strong same-event runtime witness exists but its exact path+SHA is outside the
Phase 623 candidate set. This is a contradiction to inspect, not a reason to
pick the nearest candidate.

### `multiple-exact-runtime-resource-candidates`

More than one distinct Phase 623 candidate receives exact strong same-event
runtime evidence. The stage fails closed and preserves the tie.

## LOD semantics

When the selected Phase 623 candidate belongs to a source-backed LOD family, the
exact runtime resource witness proves which child resource was actually drawn.
Phase 623's source-backed LOD parent/slot/serialized-distance provenance remains
attached to the selected candidate.

No `_lod*` filename heuristic is used for selection, and zero serialized LOD
distances continue to preserve the recovered runtime fallback rule rather than
inventing an effective threshold.

## Repeated instances

Phase 624 deliberately separates:

- **resource draw identity** — which exact IMB/LOD resource generated the draw;
- **scene instance identity** — which repeated SGB placement of that resource
  generated it.

The former can be closed here. The latter requires exact transform/spatial
correlation from evidence already present in the project.

## Renderer frontier

`SHIFT.D3D9RendererFrontierAudit/1` now accepts:

```text
--runtime-resource-draw <SHIFT.IMBRuntimeResourceDrawCandidateJoin/1>
```

If every Phase 623 geometry row becomes `exact-scene-resource-draw`,
`scene_resource_exact_draw_attribution` becomes `closed-offline-exact` with
confidence:

- `exact-same-event-runtime-resource-plus-static-scene-evidence`.

If only repeated instances remain, the frontier directs the next stage to
world-matrix/transform or source-backed spatial correlation and explicitly notes
that VB/IB payload is irrelevant to that distinction.

The historical absence of `buffer_payload` remains recorded by the base audit;
Phase 624 does not rewrite capture history. It only demonstrates when that
missing observation is unnecessary for the current geometry frontier.

## Regression coverage

`tests/test_imb_runtime_resource_draw_candidate_join.py` covers:

- exact same-event path+SHA selection;
- path normalization without weakening SHA equality;
- repeated scene-instance preservation;
- event-index mismatch rejection;
- weak/unattributed shader evidence rejection;
- runtime/static candidate conflicts;
- multiple exact runtime candidates;
- per-binding/resource identity disagreement;
- exact runtime resource without exact Phase 623 scene reference;
- empty input and format validation.

`tests/test_d3d9_renderer_frontier_audit.py` additionally covers Phase 624
closure, repeated-instance continuation, conflict handling, and preservation of
historical `buffer_payload` absence.
