# Phase 538 — retail BMW material-slice duplicate closure

Phase 536 made the retail BMW material-binding corpus archive-layout-safe.
Phase 537 then collapsed identical top-ranked bytecode identities and recorded
the remaining genuine material-level permutation ambiguity.

Phase 538 closes the corresponding duplicate-resource bug one layer downstream
in `bmw_real_material_slice.py`, so the full six-primitive Phase 533
orchestrator can consume the same retail BMW/Cockpit/RENDER corpus.

## Why another duplicate rule was required

The material binding and the material slice resolve resources independently.
The binding layer already accepted multiple copies of the same logical path
when their payload hashes matched. The slice layer still required exactly one
BMT/FX/DDS entry.

The retail corpus contains legitimate identical copies. In particular:

```text
vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt
```

exists in both `BMW_M3_E36.bff` and `BMW_M3_E36_Cockpit.bff` with payload
SHA-256:

```text
6dd62026600849a7fec2b29e48bcb68c61b342e7275954d6f3fe74a7be107b0a
```

The old slice resolver rejected that documented corpus before it could finish
the canonical body admission.

## Phase 538 rule

For BMT/MEB, shader source and material DDS resources:

1. zero matches remain missing evidence;
2. one match is accepted;
3. multiple matches with identical payload SHA-256 are one logical resource;
4. the deterministic first archive copy is retained for provenance;
5. multiple matches with different payload bytes remain a hard conflict.

DDS conflicts are surfaced as `material-slice:dds-conflict:<path>`.

No shader candidate is chosen by this rule.

## Six-primitive result

The full canonical body can now pass the archive/resource-resolution boundary.
The compact observation is stored in:

```text
evidence/bmw_m3_e36_retail_body_admission_observation.json
```

After the Phase 537 bytecode-identity collapse, the remaining equal top-ranked
permutation identities are:

| Primitive | Material | Family | distinct top identities |
|---:|---|---|---:|
| 0 | BMW_M3_E36_BADGING | vehiclesbasic | 18 |
| 1 | BMW_M3_E36_PAINT | bodywork | 20 |
| 2 | BMW_M3_E36_PAINT | bodywork | 20 |
| 3 | GENERIC_WINDOWS | glass | 10 |
| 4 | GENERIC_GLOSS_BLACK | vehiclesbasic | 27 |
| 5 | BMW_M3_E36_LIGHTSGLASS | glass | 10 |

The admission result remains **0 ready / 6 blocked**. The common primary reason
is `generic-material:shader-selection-not-unique`.

This is the desired fail-closed result: archive duplication is no longer
mistaken for shader ambiguity, but genuinely different shader identities are
not selected without additional evidence.

## Render-state confirmation

The same retail slices confirm the source-backed Phase 530–532 state path:

- BADGING — depth test on, depth write off, source-alpha /
  inverse-source-alpha blend;
- PAINT — depth test/write on, blending off;
- GENERIC_WINDOWS — depth test on, depth write off, one /
  inverse-source-alpha blend;
- GENERIC_GLOSS_BLACK — depth test/write on, blending off;
- LIGHTSGLASS — depth test on, depth write off, one /
  inverse-source-alpha blend.

All five BMT definitions use `EBFCT_ANTICLOCKWISE`.

## Next gate

The next BMW rendering task is concrete FXO permutation attribution. Static
ranking should only be strengthened with evidence-bearing features. If that
cannot reduce each material to one identity, same-instance D3D9 runtime shader
capture is the closure path.

The raw retail archives remain external evidence and are not committed.
