# Phase 536 — retail BMW body material corpus admission

Phase 536 executes the Phase 533 admission boundary against the retail
Need for Speed: SHIFT 1.02 BMW/renderer corpus and fixes two archive-composition
problems exposed by that run.

## Retail corpus

The evidence run used:

- `BMW_M3_E36.bff`
  - size: 18,934,688 bytes
  - SHA-256: `c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70`
- `BMW_M3_E36_Cockpit.bff`
  - size: 9,956,064 bytes
  - SHA-256: `a9bc1b3c0dfb21408913089d565fa2ffc80f2fb2c4a408ab9aef101d012f15be`
- `Pakfiles/Dir/RENDER.bff`
  - size: 2,985,696 bytes
  - SHA-256: `b0b03960ba7e620b7ad5e2b027ed13de67afffe168eb8b30da73c2a632a7c0af`

The canonical mesh remained
`vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb` with the already recorded
SHA-256 `960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c`.

The compact result is committed as
`evidence/bmw_m3_e36_retail_body_material_admission.json`.

## Identical supplemental resources are not ambiguity

The recommended Phase 533 corpus combines body, cockpit and renderer archives.
That exposed real logical resources copied into more than one archive. For
example, `BMW_M3_E36_PAINT.bmt` occurs in both vehicle archives with identical
payload SHA-256
`6dd62026600849a7fec2b29e48bcb68c61b342e7275954d6f3fe74a7be107b0a`.

Previously, `_find_exact()` rejected any count other than one. This made the
documented Phase 533 command fail on an identical retail copy.

Phase 536 changes the rule to:

1. zero matches: missing resource;
2. one match: use it;
3. multiple matches with one payload SHA-256: one logical resource, select the
   first archive in deterministic corpus order;
4. multiple matches with different payload SHA-256 values: hard conflict.

The same rule is applied to exact BMT/MEB resources, shader-source matches and
DDS resolution used by the BMW material slice.

## FXO corpus filtering and copy deduplication

The retail BMW archives contain large shader-cache corpora. Sending every FXO
from all supplemental archives into every material link caused a single
six-primitive Phase 533 run to spend minutes repeatedly reflecting unrelated
shader families.

Before reflection, Phase 536 now:

- derives the same normalized shader family used by the universal render
  pipeline;
- keeps only FXO paths belonging to the material's requested family;
- groups identical logical FXO paths across archives;
- content-deduplicates identical copies;
- blocks conflicting bytes for the same logical FXO path.

This is a search-space reduction only. It does not change
`material_linker._selection_evidence_key()` and does not invent a winning
permutation.

## Retail result

All six canonical primitives now reach the real linker with their actual
material, FX source, DDS resources and family-specific FXO corpus.

| Primitive | Material | Family | FXO files | Duplicate copies removed | Program candidates | Equal top programs | Distinct top pairs |
|---:|---|---|---:|---:|---:|---:|---:|
| 0 | BADGING | vehiclesbasic | 248 | 124 | 992 | 40 | 18 |
| 1 | PAINT | bodywork | 305 | 244 | 465 | 124 | 20 |
| 2 | PAINT | bodywork | 305 | 244 | 465 | 124 | 20 |
| 3 | GENERIC_WINDOWS | glass | 293 | 61 | 586 | 122 | 10 |
| 4 | GENERIC_GLOSS_BLACK | vehiclesbasic | 248 | 124 | 992 | 60 | 27 |
| 5 | LIGHTSGLASS | glass | 293 | 61 | 586 | 122 | 10 |

No primitive is admitted yet. The common primary blocker is
`generic-material:shader-selection-not-unique`.

The remaining ties are genuine under the current static evidence key: they
contain multiple different shader-pair hashes after duplicate archive copies
have been removed. Phase 536 therefore intentionally leaves all six draws
blocked instead of selecting by filename or stable sort order.

## Material-state confirmation

The retail BMTs also confirm the Phase 530–532 per-draw state path:

- BADGING: depth test on, depth write off, source-alpha/inverse-source-alpha
  blend;
- PAINT: depth test/write on, blend off;
- GENERIC_WINDOWS: depth test on, depth write off, one/inverse-source-alpha
  blend;
- GENERIC_GLOSS_BLACK: depth test/write on, blend off;
- LIGHTSGLASS: depth test on, depth write off, one/inverse-source-alpha blend.

All five use `EBFCT_ANTICLOCKWISE` culling.

## Next evidence step

The next render task is not another archive resolver. It is to improve
shader-permutation evidence for `vehicles_basic`, `bodywork` and `glass`
so that the existing fail-closed ranking can distinguish the retail candidate
pairs. Runtime same-instance shader attribution remains the strongest closure
path when static specialization evidence is insufficient.
