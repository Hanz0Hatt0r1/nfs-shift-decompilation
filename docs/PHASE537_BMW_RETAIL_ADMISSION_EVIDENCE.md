# Phase 537 — retail BMW body admission evidence

Phase 537 completes the first real execution of the Phase 533 six-primitive
BMW body admission against the retail 1.02 vehicle/cockpit/renderer corpus.

## Corpus

The run used the exact archives recorded in
`evidence/bmw_m3_e36_retail_body_material_admission.json`:

- `BMW_M3_E36.bff`;
- `BMW_M3_E36_Cockpit.bff`;
- `Pakfiles/Dir/RENDER.bff`.

The canonical mesh identity remains
`vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb` with SHA-256
`960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c`.

## Remaining supplemental-copy fix

Phase 536 made the material-binding linker duplicate-safe, but the downstream
material-slice builder still expected exactly one BMT, FX and DDS resource
across the combined body/cockpit/RENDER corpus.

The retail corpus disproves that assumption. The paint BMT, for example, is
present in both BMW vehicle archives with identical bytes.

Phase 537 applies the same evidence rule to the slice builder:

1. missing logical path -> missing-resource blocker;
2. one copy -> use it;
3. multiple copies with identical SHA-256 -> one logical resource, retain
   deterministic first-archive provenance;
4. multiple copies with different bytes -> fail closed as a conflict.

DDS resources use the same rule. Conflicting duplicate textures are reported
as `material-slice:dds-conflict:<path>`.

## Actual six-primitive result

All six canonical MEB primitives now reach the material linker and neutral
RenderCommand construction using the real archives.

| Primitive | Material | Shader family | FXO files | duplicate copies | program candidates | equal top candidates | distinct top pairs |
|---:|---|---|---:|---:|---:|---:|---:|
| 0 | BMW_M3_E36_BADGING | vehiclesbasic | 248 | 124 | 992 | 40 | 18 |
| 1 | BMW_M3_E36_PAINT | bodywork | 305 | 244 | 465 | 124 | 20 |
| 2 | BMW_M3_E36_PAINT | bodywork | 305 | 244 | 465 | 124 | 20 |
| 3 | GENERIC_WINDOWS | glass | 293 | 61 | 586 | 122 | 10 |
| 4 | GENERIC_GLOSS_BLACK | vehiclesbasic | 248 | 124 | 992 | 60 | 27 |
| 5 | BMW_M3_E36_LIGHTSGLASS | glass | 293 | 61 | 586 | 122 | 10 |

The result is intentionally **0 ready / 6 blocked**.

The common primary blocker is:

```text
generic-material:shader-selection-not-unique
```

These are no longer archive-copy duplicates. The tied sets contain multiple
different shader pair hashes with equal current static evidence scores.
Selecting one by path, hash order or first-match order would invent evidence.

Paint additionally exposes an ambiguous vertex-pair selection in the current
bodywork cache ranking, while the glass and vehicles_basic families expose
material/uniform/sampler blockers downstream of the same unresolved shader
identity.

## Retail render-state confirmation

The actual BMTs confirm that the source-backed Phase 530–532 state path covers
the needed basic per-draw differences:

- BADGING — depth test on, depth write off, source-alpha /
  inverse-source-alpha blending;
- PAINT — depth test/write on, blending off;
- GENERIC_WINDOWS — depth test on, depth write off, one /
  inverse-source-alpha blending;
- GENERIC_GLOSS_BLACK — depth test/write on, blending off;
- LIGHTSGLASS — depth test on, depth write off, one /
  inverse-source-alpha blending.

All five material definitions use `EBFCT_ANTICLOCKWISE` culling.

## Evidence boundary and next step

Phase 537 does not admit a best-looking FXO candidate. The next material task
is to add evidence that distinguishes the real `vehicles_basic`, `bodywork`
and `glass` permutations. Candidate ranking may only be strengthened by
observable shader features, exact compiled-interface requirements or runtime
same-instance attribution.

The raw game archives remain external evidence and are not committed.
