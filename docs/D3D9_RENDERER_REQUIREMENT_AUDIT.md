# D3D9 renderer requirement audit

## Purpose

`d3d9_renderer_requirement_audit.py` is the fail-closed decision layer for the
offline renderer evidence pipeline. It does not recover new runtime state by
itself. Instead it answers the question that must be settled before requesting a
new capture:

> Is the next proof blocked because the historical capture truly lacks a needed
> observation, or because existing evidence still needs correlation tooling?

The output format is:

`SHIFT.D3D9RendererRequirementAudit/1`

## Inputs

The audit accepts any subset of:

- `SHIFT.D3D9ShaderUseEvidence/1`;
- `SHIFT.D3D9TargetDrawLocalEvidence/1`;
- `SHIFT.D3D9TargetTextureSamplerEvidence/1`;
- `SHIFT.IMBDrawLocalAmbiguityAudit/1`.

Missing reports remain `not-evaluated`; they are not treated as missing capture
data.

## Requirement states

The audit distinguishes:

- `closed-capture-local` — an exact capture-local proof is already present;
- `present-needs-tooling` — the useful observation exists, but semantic/static
  correlation is still required;
- `ambiguous` — two or more candidates remain and no winner is selected;
- `partial-capture-local` — only part of the capture-local state is reconstructed;
- `absent-in-capture` — the producing evidence report explicitly observed zero
  usable events for that requirement;
- `no-active-blocker` — the supplied ambiguity report does not currently expose
  that ambiguity class;
- `not-evaluated` — the required upstream report was not supplied.

These states are intentionally not a ranking.

## Explicit recapture gate

An `absent-in-capture` observation does **not** automatically imply that another
capture is needed.

By default the report remains:

```text
status = continue-offline
capture_required_now = false
```

A capture-only field becomes a current blocker only when a downstream stage has
already proved that it is a hard requirement and invokes the audit with
`--require`.

Supported hard requirements are:

- `buffer_payload`;
- `sampler_state`;
- `portable_texture_identity`;
- `texture_snapshot`.

Example:

```bash
python src/graphics/d3d9/d3d9_renderer_requirement_audit.py \
  out/d3d9_renderer_requirement_audit.json \
  --shader-use out/d3d9_shader_use_evidence.json \
  --draw-local out/d3d9_target_draw_local_evidence.json \
  --texture-sampler out/d3d9_target_texture_sampler_evidence.json \
  --ambiguity out/silverstone_d3d9_draw_local_ambiguity_audit.json
```

Only after an exact geometry proof has shown that VB/IB payload equality is the
remaining indispensable discriminator should it be rerun with:

```text
--require buffer_payload
```

At that point the report names only the minimal missing observation instead of
asking for a broad replacement capture.

## Current Silverstone interpretation

The existing evidence chain already supports capture-local proof for:

- shader creation identity;
- shader bind/use identity;
- exact VS/PS byte pairing;
- exact indexed primitive ranges;
- VB/IB generation identity;
- CTAB float constant windows;
- texture creation/binding generations.

The historical capture separately lacks observations such as buffer payloads,
explicit sampler-state events, portable texture path+SHA identity and captured
texture payload snapshots where the corresponding evidence reports say so.
Those gaps remain conditional capture boundaries, not immediate capture
requests.

Phase 618 ambiguity classes remain offline work first:

- `material-distinct-candidates` -> exact BMT/DDS + draw-local sampler/constant
  correlation;
- `shader-provenance-distinct-candidates` -> exact embedded FXO VS+PS pair
  provenance;
- metadata-equivalent geometry/LOD alternatives -> exact static scene/instance
  and LOD references.

If any gate still leaves two exact candidates, the audit continues to report the
state as ambiguous.

## Output sections

The report provides:

- `requirements` — the full requirement ledger;
- `existing_data_requiring_tooling` — work that should be exhausted offline;
- `genuinely_absent_capture_observations` — observations explicitly absent in
  the supplied evidence reports;
- `capture_blockers` — absent observations that were also explicitly declared a
  hard requirement;
- `conditional_minimal_capture` — the smallest observation that would be needed
  *if* its corresponding downstream proof later becomes mandatory.

## Non-claims

The audit never claims:

- that one surviving static candidate is exact retail identity;
- that a filename/LOD suffix is proof;
- that a pathless texture is external/runtime-owned;
- that an FXO ranking is a permutation identity;
- that transform-like constant names prove world-matrix semantics;
- that any candidate is ready for Vulkan render admission.
