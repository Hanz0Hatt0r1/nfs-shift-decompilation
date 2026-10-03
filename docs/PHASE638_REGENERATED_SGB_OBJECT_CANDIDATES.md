# Phase 638 — regenerated SGB runtime object candidates

Phase 638 removes `SHIFT.SGBRuntimeObjectCandidateJoin/1` from the set of scene
reports that must be prepared manually before repeated-instance renderer
analysis.

The new entry point is:

```text
tools/run_silverstone_renderer_object_candidate_regeneration.py
```

It consumes:

- source BFF/ZIP corpus;
- regenerated `SHIFT.IMBRuntimeCapturePipeline/1` from Phase 630.

No original game execution and no new capture are required.

## Source graph

Phase 638 reuses the existing source-backed scene and IR builders:

```text
BFF/ZIP corpus
  -> offline_scene_ir.build_scene_ir()
     -> manifest.json

all .sgb occurrences in every materialized BFF
  -> sgb_runtime.parse_sgb_runtime(strict=False)
     SHIFT.SGBRuntime/1
  -> sgb_placement_join.build_sgb_placement_join()
     SHIFT.SGBPlacementJoin/1
  -> sgb_scene_placement.build_sgb_scene_placement()
     SHIFT.SGBScenePlacement/1
  -> sgb_object_render_handoff.build_sgb_object_render_handoff_set()
     SHIFT.SGBObjectRenderHandoffSet/1

scene placement + object handoffs
+ Phase 630 runtime capture pipeline
+ exact IR manifest
  -> sgb_runtime_object_candidate_join.build_runtime_object_candidate_join()
     SHIFT.SGBRuntimeObjectCandidateJoin/1
```

The Phase 638 orchestration manifest is:

```text
SHIFT.SilverstoneRendererObjectCandidateRegeneration/1
```

Every SGB occurrence is evaluated independently and its intermediate reports are
persisted under `sgb-candidates/`.

## No filename-based scene selection

The corpus may contain several SGB resources. Phase 638 does not assume that a
file named like Silverstone, a first SGB in archive order, or a frequent logical
resource path is the active scene.

A ready SGB occurrence must independently pass the existing runtime object join:

- exact runtime archive identity;
- normalized runtime resource path;
- exact runtime resource SHA-256;
- existing same-instance attribution gate;
- revalidation against the generated IR manifest;
- at least one matching source-backed SGB object candidate per runtime resource.

Ready occurrences are grouped by:

```text
exact SGB payload SHA-256
+ canonical SHIFT.SGBRuntimeObjectCandidateJoin/1 payload SHA-256
```

Several occurrences may collapse only when both identities are exact. This
allows byte-identical duplicate SGB copies to retain all archive provenance
without fabricating a second scene.

If two different SGB payload hashes are independently ready, Phase 638 remains
blocked with scene-level ambiguity. Equal logical paths are not sufficient to
collapse different SGB bytes.

## Object identity boundary

`SHIFT.SGBRuntimeObjectCandidateJoin/1` remains a candidate report, not render
admission.

A ready report proves that each runtime resource can be tied to source scene
objects through the existing exact runtime identity gate. It may still contain
multiple logical scene candidates for one runtime resource because the SGB
object contract does not itself carry source archive identity for the referenced
resource.

Therefore:

- `ready=true` does not imply `identity_complete=true`;
- one logical candidate is not automatically portable object identity;
- object candidate selection is not a world-transform proof;
- the join does not authorize draw admission.

These boundaries are inherited unchanged from Phase 595.

## MultiMatrix second pass

Initial object/resource attribution does not require a numeric MultiMatrix root.
This is deliberate: resource identity and transform-state recovery are separate
proof dimensions.

For every initially ready SGB object join, Phase 638 additionally runs the
existing Phase 596:

```text
SHIFT.SGBRuntime/1
+ initial SHIFT.SGBRuntimeObjectCandidateJoin/1
+ SHIFT.IMBRuntimeCapturePipeline/1
  -> SHIFT.SGBMultiMatrixRootConsensus/1
```

Phase 596 searches all contiguous four-register strong-attributed VS constant
windows, accepts row-major and transpose layouts, round-trips them through the
source-backed Phase 594 inverse solve, and requires independent support from at
least two exact runtime resources with at least two distinct cumulative local
transforms.

When Phase 596 reports ready consensus, Phase 638 rebuilds the object handoff set
with that consensus and reruns the runtime object join. The enriched report may
therefore contain numeric world matrices for parent-MultiMatrix objects.

If no root consensus is found, the initial object join remains valid. Missing
root consensus is not a scene-selection contradiction and is not a recapture
request. It simply leaves the transform gate unresolved for placements that
need it later.

## IR manifest boundary

Phase 638 regenerates the renderer IR through `offline_scene_ir.build_scene_ir()`
using the same source corpus. The generated `manifest.json` is passed directly
to the existing object join, which revalidates runtime archive/path/SHA
identities.

The legacy importer manifest is not itself render admission. Its heuristic
legacy dependency hints and basename fallback remain non-proof. Phase 638 uses
it only through the exact identity checks already implemented by the object
candidate join.

If scene IR materialization is blocked, SGB scene selection does not run.

## Selection policy

Phase 638 explicitly forbids:

- selecting an SGB by filename;
- selecting the first SGB in archive order;
- selecting by occurrence count or frequency;
- collapsing different SGB payloads because their resource paths look equal;
- treating root-consensus failure as evidence for or against a scene;
- treating object candidate readiness as render admission.

The only automatic scene collapse is exact duplicate content plus exact
canonical candidate-join identity.

## Capture boundary

Phase 638 uses only observations already present in the historical capture and
Phase 630 pipeline. It introduces no dependency on historically absent:

- `SetSamplerState` history;
- VB/IB payload bytes;
- portable texture snapshots;
- new runtime resource captures.

Phase 596 consumes the existing strong-attributed constant state already present
in the capture.

Therefore:

```text
original game execution required: no
new capture required: no
```

## Production consequence

Once Phase 638 is integrated after Phase 630, Phase 625 repeated-instance
analysis can receive a regenerated object-candidate join rather than a bundle
handoff. When Phase 596 can also prove the relevant MultiMatrix roots, the same
source path supplies numeric world matrices needed by the Phase 625 exact
same-draw float32 transform comparison.

If several distinct SGB payloads remain fully runtime-compatible, that scene
ambiguity must remain explicit until another source-backed scene-selection
dimension is proven.
