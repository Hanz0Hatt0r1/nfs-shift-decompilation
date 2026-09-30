# Phase 597 — promote consensus roots into MatrixNumber handoffs

Phase 596 can authorize one current MultiMatrix root for an SGB wrapper when
independent runtime resources using distinct local chains converge to the same
exact float32 root.

Phase 597 consumes that authorization before scene render admission.

## Contract

The new adapter is:

`src/scene/sgb_multimatrix_root_promotion.py`

It consumes:

- `SHIFT.SGBRuntime/1`;
- `SHIFT.SGBMultiMatrixRootConsensus/1`.

It emits the existing downstream contract:

`SHIFT.SGBObjectRenderHandoffSet/1`

with an additional `SHIFT.SGBMultiMatrixRootPromotion/1` summary.

This keeps `SHIFT.SGBRenderBindingAdmission/1` unchanged.

## Admission policy

Only consensus rows satisfying all of these are consumed:

- consensus report itself is ready;
- row is ready;
- `authorizes_current_wrapper_root = true`;
- wrapper identity is exact `NODE|SUMM + source_record_index`;
- wrapper exists in the supplied SGB runtime;
- root is one finite numeric 4x4 matrix.

The Phase 596 boundary must continue to state:

- current wrapper root only;
- SceneGraph update history not recovered;
- direct render admission not authorized.

Any violation is rejected before handoff rebuilding.

## Handoff integration

`build_sgb_object_render_handoff_set()` now accepts an optional wrapper-root
map.

For OBJECT rows using `MatrixNumber >= 0`, that root is passed to the existing
`build_object_render_handoff()` path. No new matrix arithmetic is introduced.

The existing MultiMatrix evaluator remains the only world-matrix materializer:

```text
authorized wrapper root
  → existing MultiMatrix local hierarchy
  → selected MatrixNumber world slot
  → ordinary SGBObjectRenderHandoff
```

Explicit OBJECT transforms are unchanged.

## Promotion summary

The emitted handoff set records:

- number of authorized wrapper roots;
- OBJECT rows to which a wrapper root was supplied;
- MatrixNumber rows that changed from non-numeric to numeric world matrices;
- MatrixNumber rows still unresolved.

Each affected OBJECT row retains compact Phase 596 provenance including support
resource count, distinct local-chain count and witness count.

## Scene admission

Phase 597 does not bypass scene admission.

A promoted handoff still enters the existing
`SHIFT.SGBRenderBindingAdmission/1`, which independently requires:

- placement readiness;
- resource reference;
- numeric world matrix;
- spatial culling readiness.

The promotion contract explicitly keeps
`direct_render_admission_authorized = false`.

## Historical update sequence

This phase resolves current numeric state only.

It does not claim:

- which SceneGraph event changed the root;
- when that event occurred;
- a recovered retail update sequence;
- a retail world-constant register semantic.

The full historical SceneGraph update sequence remains a separate evidence
question.

## CLI

```bash
python shift_importer.py sgb-multimatrix-root-promotion \
  out/sgb-runtime.json \
  out/multimatrix-root-consensus.json \
  out/root-promoted-object-handoffs.json
```

The resulting handoff file can be passed directly to
`sgb-render-binding-admission`.

## Next

The remaining scene-side evidence work is no longer the mechanical
MatrixNumber promotion itself. The next blockers are authentic Silverstone
capture coverage for wrappers/resources without enough runtime evidence,
remaining renderer-owned resource types, and the unrecovered historical
SceneGraph update sequence.
