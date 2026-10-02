# Phase 614 — capture-local pointer candidate join

## Purpose

Phase 611/612 narrows the 39 target D3D9 resource shapes using static IMB
geometry plus BMT/DDS descriptors. Some resource shapes remain ambiguous because
different retail resources legitimately share the same geometry/material
descriptor contract.

Phase 613 preserves the historical capture's runtime VB/IB/texture object
generations without changing the stable Phase 605 resource-shape SHA.

Phase 614 joins those two evidence layers. A resource shape that is already a
Phase 611 `single-content-candidate` may seed the same **combined pointer
identity** when that exact runtime object generation is observed under another
resource shape.

The output format is:

`SHIFT.IMBRuntimePointerCandidateJoin/1`

## Why the join is per pointer identity

A descriptor-equivalent resource shape can contain several actual runtime
objects. Therefore it is unsafe to narrow an entire 103-draw shape merely
because one of its objects also appeared in a known single-content shape.

Phase 614 operates on each Phase 613 `combined_pointer_observation` separately.
An ambiguous resource shape may therefore contain:

- pointer identities reduced to one static content candidate;
- pointer identities that remain ambiguous;
- several different single contents, each attached to a different runtime
  object generation.

This preserves the distinction that descriptor aggregation intentionally loses.

## Seed rule

A combined pointer identity is seedable only when it appears in a Phase 611
resource shape with exactly one surviving static content group.

If the same runtime pointer identity is seeded by more than one distinct content
group, its seed status becomes `conflicting-content-seeds` and it is never used
to narrow candidates.

A unique seed may narrow an ambiguous pointer observation only when the seeded
content group is already present in that observation's Phase 611 static
candidate set. A seed outside the static candidate set fails closed as
`seed-outside-static-candidate-set`.

## Gate statuses

Per pointer identity:

- `already-single` — Phase 611 had one candidate already;
- `reduced-by-same-object-seed` — an ambiguous static set was reduced by an
  identical runtime object generation;
- `no-seed` — no single-content resource shape observed the same object;
- `conflicting-pointer-seeds` — different single-content rows assigned
  different contents to the same pointer identity;
- `seed-outside-static-candidate-set` — pointer evidence conflicts with the
  current static candidate set;
- `no-base-candidates` — no static content candidates exist.

## Capture-local identity

The combined identity comes directly from Phase 613 and contains:

- device pointer;
- stream-0 VB pointer + creation event index;
- IB pointer + creation event index;
- exact draw range;
- CTAB-filtered texture pointers + creation event indices.

Creation event indices are part of identity so a COM address reused for a later
resource is not treated as the same object.

## Boundary

This remains candidate-only evidence.

Pointer continuity proves only that two observations refer to the same runtime
object generation inside this one capture. It does not prove:

- retail BFF/IMB path;
- IMB or DDS payload SHA-256;
- portable identity across executions;
- render admission.

Even a `reduced-by-same-object-seed` result inherits the Phase 611 seed's
candidate-only boundary. Promotion still requires exact runtime resource
path/SHA or raw payload equality plus the existing Phase 572 strong
same-instance gates.

## CLI

After generating Phase 613:

```bash
python src/scene/imb_runtime_pointer_candidate_join.py \
  out/d3d9_target_pointer_observations.json \
  out/d3d9_runtime_material_descriptor_candidate_join.json \
  out/d3d9_runtime_pointer_candidate_join.json
```

The most useful summary fields are:

- `newly_resolved_pointer_identity_count`;
- `newly_resolved_pointer_identity_draw_count`;
- `pointer_seed_conflict_identity_count`;
- `pointer_candidate_gate_status_counts`.

A zero newly-resolved count is still a useful result: it means the historical
capture cannot bridge the remaining ambiguity by same-object continuity and the
next step should move to raw buffer/texture payload capture rather than inventing
another descriptor heuristic.
