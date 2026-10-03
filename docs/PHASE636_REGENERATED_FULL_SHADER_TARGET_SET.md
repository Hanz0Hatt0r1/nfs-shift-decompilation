# Phase 636 — regenerated full runtime shader target set

Phase 636 removes the full `SHIFT.IMBRuntimeShaderTargetSet/1` from the set of
renderer reports that must be prepared manually before self-bootstrap
production.

The new entry point is:

```text
tools/run_silverstone_renderer_shader_target_regeneration.py
```

It regenerates the full per-binding target contract directly from source
BFF/ZIP corpus data. No original game execution or new runtime capture is
required.

## Source graph

The stage composes two existing source-backed builders:

```text
BFF/ZIP corpus
  -> audit_imb_material_shader_ranking()
     SHIFT.IMBMaterialShaderRanking/1
  -> build_imb_runtime_shader_target_set()
     SHIFT.IMBRuntimeShaderTargetSet/1
```

The material/shader ranking traverses concrete IMB primitive contexts and uses:

- decoded IMB resource identity and primitive draw range;
- same-archive BMT material resolution;
- exact referenced FX source;
- shader family;
- deduplicated same-family FXO payloads;
- IMB vertex properties;
- the existing material-linker evidence ordering.

The target-set builder then converts every **complete top-rank candidate set**
into capture targets while retaining all candidate variants.

## Ambiguity is preserved

A ranking row does not need to select one retail shader permutation for the
runtime target set to be capture-ready.

For an ambiguous row, every tied top-rank candidate is preserved. Phase 636
therefore does not turn the static ranking heuristic into render admission.

The relevant contract remains:

```text
ambiguous static selection
!= missing target evidence
!= permission to pick the first candidate
```

The full target set records candidate variants, pixel/vertex/pair/permutation
hashes where available, resource identity, source draw range and per-binding
readiness.

## Compact Phase 568 evidence

The committed file:

```text
evidence/silverstone_era3_runtime_shader_targets.json
```

has the compact format:

```text
SHIFT.IMBRuntimeShaderTargetSetEvidence/1
```

It is not used to reconstruct candidate variants.

Phase 636 may use it as an independent semantic projection cross-check. The
regenerated full target set is projected to the compact evidence dimensions:

- source ranking primitive count;
- unique ranking context count;
- ranking selection-status counts;
- binding target count;
- capture-ready and exact-pair-attribution-ready binding counts;
- unique/strong/prefilter target counts;
- target identity-kind counts;
- per-binding target-count distribution;
- shader-family pixel hash sets;
- aggregate capture/attribution readiness boundary.

The compact report is projected to the same structure. Exact canonical equality
of those projections is accepted. A projection mismatch blocks instead of
silently preferring either source.

This cross-check cannot supply a missing candidate variant because the compact
report intentionally does not contain that information.

## Readiness

The Phase 636 manifest format is:

```text
SHIFT.SilverstoneRendererShaderTargetRegeneration/1
```

The stage is ready only when:

- source corpus inputs exist;
- ranking generation succeeds;
- a full `SHIFT.IMBRuntimeShaderTargetSet/1` is generated;
- the target set reports `capture_ready=true`;
- at least one binding target exists;
- any requested compact-evidence projection cross-check matches.

Ranking `ready=false` does not by itself block Phase 636. For Silverstone the
important historical state is precisely that many concrete primitive contexts
remain statically ambiguous while their complete tied candidate sets are valid
runtime capture targets.

## Proof boundary

Phase 636 does not change underlying ranking semantics:

- file order is not proof;
- candidate frequency is not proof;
- tied top-rank candidates are retained;
- the target set does not select a retail permutation;
- capture-ready targets are not render admission;
- compact Phase 568 evidence is cross-check only;
- no missing runtime event is inferred from static ranking.

Therefore:

```text
original game execution required: no
new capture required: no
```

## Production consequence

After Phase 636, Phase 635 self-bootstrap production can regenerate its own full
runtime shader target set before Phase 630. Once integrated, the core renderer
bootstrap will no longer need manually prepared draw-local, capture-pipeline,
Phase 618, base-audit, or full-target-set JSON handoffs.

The remaining conditional external evidence is then limited primarily to
source corpus availability and, when repeated scene placements require it, the
source-backed scene/object candidate path used by Phase 625.
