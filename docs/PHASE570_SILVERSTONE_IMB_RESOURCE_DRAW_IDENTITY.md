# Phase 570 — Silverstone IMB resource and draw identity

Phase 568 builds a complete shader-hash target set and Phase 569 can filter raw
D3D9 captures by that whitelist. Shader identity alone is not enough to prove
that an observed draw belongs to a particular track primitive.

Phase 570 closes the static half of that same-instance join by carrying exact
IMB resource identity and source-backed primitive draw ranges through the
ranking/target contracts.

## Ranking provenance

`tools/audit_imb_material_shader_ranking.py` now decodes each IMB payload once
and records:

- archive-local IMB path;
- BFF entry index;
- SHA-256 of the decoded IMB payload;
- primitive index;
- `first_index`;
- `index_count`;
- derived triangle/primitive count.

The draw range comes directly from the Phase 559/560 primitive index payload.
For multi-primitive IMBs, `first_index` is the cumulative offset into the
neutral combined index stream.

## Target-set readiness split

`SHIFT.IMBRuntimeShaderTargetSet/1` now exposes a second, stricter readiness
level in addition to the existing shader-capture gate.

### capture_ready

Unchanged from Phase 568. It means the complete top-rank shader candidate set is
available as runtime-observable byte hashes.

This is enough for the Phase 569 raw shader prefilter.

### same_instance_match_ready

A binding is ready for the future resource/draw matcher only when all of these
are true:

- its shader target set is `capture_ready`;
- it has an archive-local `.imb` resource path;
- it has a valid decoded IMB SHA-256;
- its indexed draw range has a non-negative `first_index`;
- `index_count` is positive and triangle-aligned;
- an optional declared primitive count agrees with `index_count / 3`.

Missing resource/draw provenance does not retroactively make shader filtering
unusable. It blocks only the same-instance matching layer.

The target-set report therefore carries:

- `resource_identity_ready_count`;
- `draw_range_ready_count`;
- `same_instance_match_ready_count`;
- `same_instance_match_ready`;
- per-binding `runtime_identity_blocking_reasons`.

## Silverstone production result

The supplied Silverstone Era3 visual corpus contains:

- 427 IMB resource occurrences;
- 428 primitive bindings;
- 181 logical IMB resource paths;
- 181 unique decoded IMB SHA-256 identities.

All **428 / 428** primitive bindings have exact resource identity and a valid
draw range.

No logical IMB path has multiple decoded hashes across the supplied track
variants.

The primitive-count distribution is:

| Primitives per IMB occurrence | IMB occurrences |
|---:|---:|
| 1 | 426 |
| 2 | 1 |

The only two-primitive resource is:

`tracks/_data/instances/gen_tent18_loda.imb`

in `Silverstone_Era3_Drift.bff`.

Its source-backed ranges are:

| Primitive | first_index | index_count | triangles |
|---:|---:|---:|---:|
| 0 | 0 | 96 | 32 |
| 1 | 96 | 24 | 8 |

The ranges are contiguous and non-overlapping.

Across the full corpus the smallest primitive range contains 6 indices and the
largest contains 3,072.

## Frozen evidence

The compact production result is committed as:

`evidence/silverstone_era3_runtime_resource_draw_identity.json`.

It freezes:

- the 428/428 readiness counts;
- logical/resource/hash cardinalities;
- primitive-count distribution;
- the exact two-primitive resource boundary.

## Boundary

This phase proves the static resource/draw side of future same-instance
correlation. It does not claim that any runtime draw has already been matched.

The evidence remains explicit:

- runtime same-instance observation: not evaluated;
- runtime shader observation: not evaluated.

## Next

The next step is a generic IMB runtime target matcher over
`SHIFT.D3D9RuntimeBindingEvidence/1`.

For each candidate draw it must require all three dimensions together:

`exact IMB resource identity + exact primitive draw range + target shader
hash`

and only promote a shader candidate when the runtime same-instance gate also
covers that draw.
