# Phase 574 — runtime-proven IMB shader admission

Phase 573 can execute the complete Silverstone capture-attribution path. Phase
574 adds the first post-attribution contract: it converts only runtime-proven
Phase 572 results into an explicit static shader-selection admission.

The contract is:

`SHIFT.IMBRuntimeShaderAdmission/1`

implemented in:

`src/scene/imb_runtime_shader_admission.py`.

## Input

The admission consumes:

- the exact `SHIFT.IMBRuntimeShaderTargetSet/1` used for capture;
- one or more `SHIFT.IMBRuntimeShaderVariantMatch/1` reports.

It does not accept raw shader hashes or Phase 569 prefilter hits directly.

## Required proof

A row is admitted only when all of these remain true when joined back to the
static target set:

- Phase 572 marked the binding `attributed=true`;
- the selected runtime score is at least 80;
- runtime resource path and SHA-256 equal the target binding IMB identity;
- result path/SHA also equal the static binding;
- primitive index matches;
- source-backed first/index/primitive counts match;
- the binding passed the Phase 570/571 static same-instance readiness gate;
- the selected variant identity exists in the preserved static
  `candidate_variants[]` set.

This deliberately rechecks the join instead of trusting an opaque match report.

## Content-equivalent locations

One runtime-proven shader identity may exist at multiple byte-equivalent static
FXO locations. Phase 574 does not break such ties by filename or archive order.

The admission records every equivalent location as provenance while admitting
the shared content identity.

## Partial evidence

A match report may contain a mixture of attributed and blocked primitive rows.

Phase 574 therefore supports a `partial` state:

- proven rows are emitted under `admitted_bindings`;
- unproven rows remain under `rejected_bindings` with explicit reasons.

This lets later rendering work consume only proven rows without requiring one
capture to close every Silverstone primitive at once.

## Boundary

An admitted row authorizes a **shader selection identity**, not a render draw.

Every admitted row records:

`shader_selection_admitted = true`

and:

`render_admission = false`.

It still does not contain the complete linked GLSL/uniform/sampler state needed
by `SHIFT.StaticDraw/1` and `SHIFT.RenderCommand/1`.

## Next

The next implementation step is to use one admitted runtime identity to
re-select the corresponding full FXO candidate inside `material_linker`,
rebuilding the shader pair, linked shader code, uniform binding and sampler
register assignments from the original BMT/FX/FXO inputs.

Only that reconstructed `SHIFT.MaterialBinding/1` may proceed to generic
StaticDraw/RenderCommand admission.
