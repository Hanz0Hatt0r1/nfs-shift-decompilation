# Phase 567 — Silverstone production shader-ranking closure

Phase 567 executes the Phase 566 material/geometry-aware ranking contract over
the complete supplied Silverstone Era3 visual corpus plus retail `RENDER.bff`.

The input surface is:

- 427 source-backed v0.4 IMB resources;
- 428 concrete IMB primitive/material bindings;
- 239 distinct archive-local material ranking contexts;
- the five exact FX source families recovered in Phase 564;
- the 368 distinct decoded FXO payloads inventoried in Phase 565.

## Production result

Every primitive binding reaches a valid static ranking result:

| Selection state | Primitive bindings |
|---|---:|
| unique | 0 |
| ambiguous | 428 |
| heuristic | 0 |
| none | 0 |

All 239 distinct material/geometry ranking contexts are also ambiguous.

This is an important closure: the blocker is no longer missing data, failed
shader parsing, missing material state or an unsupported vertex layout. Static
evidence genuinely leaves multiple retail-equivalent top-ranked shader
identities for every Silverstone primitive.

## Ambiguity width

The number of tied top-rank permutation identities per primitive is:

| Tied candidates | Primitive bindings |
|---:|---:|
| 5 | 37 |
| 6 | 156 |
| 20 | 118 |
| 30 | 20 |
| 40 | 25 |
| 60 | 48 |
| 120 | 24 |

No primitive is silently resolved by filename, archive order or cache hash.

## Family result

| Family | Primitive bindings | Rank contexts | Distinct tied permutation identities |
|---|---:|---:|---:|
| basic_instanced | 238 | 114 | 11 |
| crowd_geninstanced | 84 | 40 | 20 |
| crowd_geninstanced_billboard | 61 | 44 | 10 |
| foliage_instanced | 37 | 37 | 5 |
| skintest_instanced | 8 | 4 | 5 |

Across all five families the tied surface collapses to **51 distinct
`SHIFT.ShaderPermutationIdentity/1` hashes**.

That is much smaller than the original 1,280 FXO copies and 368 decoded payload
identities, but still not small enough to justify a static selection.

## Vertex-layout correlation

The production ranking includes the exact IMB Type/Usage/Channel property tuple
for each primitive owner. The observed layouts include:

- `200,460,220,130`;
- `200,460,220,240,250,130`;
- `200,460,220,240,250,130,231`;
- `200,460,220,240,250,130,580,310`.

Thus the surviving ambiguity remains after concrete vertex-format and
skinning compatibility are applied.

## Evidence

The frozen production summary is:

`evidence/silverstone_era3_material_shader_ranking.json`

It records:

- archive fingerprints;
- complete selection-state counts;
- per-family primitive/context counts;
- ambiguity-width distributions;
- all 51 surviving tied permutation identities.

## Boundary

Phase 567 closes **static ranking**, not runtime attribution.

The correct next step is the same pattern already used by the BMW slice:
convert every ambiguous primitive context into a runtime shader target set and
match it against same-instance D3D9 draw evidence.

Until that correlation is available, none of the 428 primitive bindings is
promoted to a unique retail shader permutation.
