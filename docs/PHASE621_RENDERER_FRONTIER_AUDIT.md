# Phase 621 — renderer frontier audit

The base renderer requirement audit intentionally answers whether evidence is
present, missing, ambiguous, or still requires tooling. Phases 619 and 620 add
new exact offline evidence after that audit was introduced, so the blocker view
must be updated without rewriting historical capture facts.

Phase 621 adds:

`SHIFT.D3D9RendererFrontierAudit/1`.

It folds later exact reports back into the existing requirement set while
preserving every genuinely absent capture observation and every explicit hard
capture requirement.

## Inputs

- `SHIFT.D3D9RendererRequirementAudit/1`;
- optional `SHIFT.IMBFXOPairProvenance/1` from Phase 619;
- optional `SHIFT.IMBMaterialConstantCandidateJoin/1` from Phase 620.

## FXO frontier

`fx_fxo_exact_candidate_reduction` becomes `closed-offline-exact` only when the
Phase 619 report is ready and has zero missing required shader-provenance pairs.
The evidence records the number of exact byte pairs verified from the retail FXO
corpus.

A partial Phase 619 result remains `present-needs-tooling`; it never falls back
to ranking, frequency, file order, or a capture request.

## Material frontier

`material_bmt_correlation` becomes `closed-offline-exact` only when every
material-distinct draw reported by Phase 620 was reduced to one candidate by the
strict exact-constant rule.

If Phase 620 resolves only part of the set, the requirement remains
`present-needs-tooling` and the next step is restricted to the unresolved rows:
BMT/DDS sampler descriptor/content evidence is applied before texture-payload
recapture is considered.

If there are no material-distinct draws, the requirement becomes
`no-active-blocker`.

## Capture policy preservation

Phase 621 does not infer a new hard capture requirement. Existing
`capture_blockers` from the base audit are copied unchanged.

Likewise, observations such as historical absence of `buffer_payload`, portable
resource path/SHA, sampler-state writes, or texture snapshots remain listed as
absent even when unrelated offline blockers are closed.

This separation is intentional:

```text
observation absent from historical capture
!=
observation required now
```

Only an explicit hard requirement in the base audit can make the frontier status
`capture-required`.

## CLI

```bash
python src/graphics/d3d9/d3d9_renderer_frontier_audit.py \
  out/d3d9_renderer_requirement_audit.json \
  out/d3d9_renderer_frontier_audit.json \
  --fxo-provenance out/silverstone_fxo_pair_provenance.json \
  --material-constants out/silverstone_material_constant_candidate_join.json
```

Both later reports are optional so the frontier can be refreshed incrementally.

## What is closed

When the corresponding inputs are complete, the frontier can now explicitly
mark these blockers closed without any new capture:

- exact static FXO VS/PS pair provenance;
- exact BMT numeric constant discrimination for all material-distinct rows that
  Phase 620 fully resolves.

## What remains

Depending on the concrete production reports, remaining blockers can include:

- material rows not separated by numeric constants;
- exact BMT/DDS sampler/content correlation for those rows;
- metadata-equivalent LOD/geometry alternatives;
- exact scene-instance/resource identity;
- VB/IB payload equality only where static scene evidence cannot close geometry;
- sampler-state or texture payload observations only when a downstream proof
  specifically requires them.

The audit does not manufacture a winner from ambiguity and does not convert an
absent optional capture event into a recapture request.
