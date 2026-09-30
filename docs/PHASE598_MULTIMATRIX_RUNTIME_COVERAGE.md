# Phase 598 — MatrixNumber runtime coverage audit

Phase 595 narrows exact runtime IMB resources to pre-admission SGB candidates.
Phase 596 authorizes current MultiMatrix owner roots only through independent
cross-resource/local-chain consensus. Phase 597 feeds those roots back into the
ordinary OBJECT handoff evaluator before scene admission.

Phase 598 combines those existing gates into one production coverage report.

## Contract

New module:

`src/scene/sgb_multimatrix_runtime_coverage.py`

emits:

`SHIFT.SGBMultiMatrixRuntimeCoverage/1`.

It consumes:

- `SHIFT.SGBScenePlacement/1`;
- `SHIFT.SGBRuntime/1`;
- `SHIFT.IMBRuntimeCapturePipeline/1`;
- the analyzed IR `manifest.json`.

No new transform inference is introduced.

## Execution chain

The audit runs the existing contracts in this order:

```text
baseline SGBObjectRenderHandoffSet
  + scene placement
  + exact runtime capture / IR identity
    ↓
Phase 595 SGBRuntimeObjectCandidateJoin
    ↓
Phase 596 SGBMultiMatrixRootConsensus
    ↓
Phase 597 root application through SGBObjectRenderHandoffSet
    ↓
ordinary SGBRenderBindingAdmission
```

If Phase 596 does not produce a ready owner consensus, the promoted handoff
stage remains identical to the baseline for that owner.

## Measured coverage

The report records:

- runtime resource count;
- runtime resources matched to pre-admission scene candidates;
- MatrixNumber OBJECT count;
- baseline numeric MatrixNumber count;
- ready owner-consensus count;
- ambiguous owner-consensus count;
- consensus hypothesis/eligible-root counts;
- MatrixNumber OBJECTs newly resolved by consensus;
- MatrixNumber OBJECTs still unresolved;
- promoted numeric MatrixNumber count;
- baseline admitted scene binding count;
- promoted admitted scene binding count;
- bindings newly admitted only after consensus application.

Resolved and unresolved OBJECT rows preserve:

- wrapper identity;
- object path;
- exact owner path;
- resource reference;
- MatrixNumber;
- current root source;
- compact Phase 596 consensus provenance.

## Readiness

The audit is `ready` only when the runtime capture pipeline is ready and the
Phase 595 runtime-object candidate join is ready.

A valid capture may still produce zero ready owner consensuses. That is a
measured evidence result, not a guessed root.

When same-instance resource evidence is incomplete, the coverage report is
blocked and downstream promotion remains zero.

## Scene admission delta

Phase 598 evaluates scene admission both before and after Phase 597.

This makes the impact explicit:

```text
baseline MatrixNumber numeric world
  → promoted MatrixNumber numeric world
  → ordinary scene binding ready transition
```

No binding is counted as newly admitted unless the existing
`SHIFT.SGBRenderBindingAdmission/1` independently accepts it.

## Boundary

Phase 598 does not:

- assign a retail world-matrix register;
- recover SceneGraph event history;
- infer missing runtime resources;
- bypass Phase 595/596/597 evidence gates;
- bypass normal spatial/resource/numeric scene admission.

It is a measurement/orchestration layer only.

## CLI

```bash
python shift_importer.py sgb-multimatrix-runtime-coverage \
  out/scene-placement.json \
  out/sgb-runtime.json \
  out/silverstone-runtime-attribution.json \
  out/ir \
  out/multimatrix-runtime-coverage.json
```

## Production use

With authentic Silverstone D3D9 capture content, this report is the canonical
way to answer:

- how many runtime resources can support Phase 596;
- how many MultiMatrix owners obtain a ready current root;
- how many previously blocked MatrixNumber OBJECTs become numeric;
- how many scene bindings become newly admissible;
- which owners still need additional runtime evidence.

Until authentic capture content exists for the required resources, the tool
remains ready for execution but does not fabricate production counts.
