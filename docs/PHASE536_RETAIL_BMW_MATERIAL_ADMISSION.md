# Phase 536 — retail BMW material admission corpus

Phase 536 executes the Phase 533 material-selection boundary against the real
v1.02 BMW body corpus:

- `BMW_M3_E36.bff`
- `BMW_M3_E36_Cockpit.bff`
- `RENDER.bff`

Raw retail binaries are not committed. Their sizes and SHA-256 identities are
recorded in
`evidence/bmw_m3_e36_retail_material_admission_observation.json`.

## Corpus normalization fixes

The retail run exposed two issues before material evidence could be interpreted:

1. `bmw_material_from_bff.py` used `re` without importing it.
2. Every FXO in every supplemental archive was sent to the linker, regardless
   of the material's referenced FX family.

Phase 536 fixes both. FXO inputs are now restricted to the normalized shader
family, for example:

```text
render/shaders/bodywork.fx
  -> render_shaders_bodywork_*.fxo
```

Duplicate resources with the same normalized path are accepted only when their
bytes are identical. Conflicting duplicate resources remain a hard error.

The material linker also collapses top-scoring candidates that have the same
proven permutation/pair byte identity. File name and program offset are used as
identity only when byte hashes are unavailable.

## Retail result

The canonical body LODA has six primitives using five unique materials.

All five unique materials resolve:

- their exact BMT;
- the referenced FX source;
- all material texture paths required by the linker.

After family filtering and duplicate-copy collapse, all five remain blocked on
**real shader-permutation ambiguity**.

Observed shader-family candidate populations are:

| Material | Family | FXO candidates | duplicate copies |
|---|---|---:|---:|
| BADGING | vehicles_basic | 248 | 124 |
| PAINT | bodywork | 305 | 244 |
| GENERIC_WINDOWS | glass | 293 | 61 |
| GENERIC_GLOSS_BLACK | vehicles_basic | 248 | 124 |
| LIGHTSGLASS | glass | 293 | 61 |

For BADGING, WINDOWS, GLOSS_BLACK and LIGHTSGLASS the remaining gate is
`generic-material:shader-selection-not-unique`.

PAINT additionally retains its stricter pair/linkage blockers because the
highest-ranked bodywork pixel candidate still has multiple compatible vertex
pair identities.

## Evidence boundary

Phase 536 deliberately does not select the first or highest-ranked distinct
FXO permutation. Such a choice would be heuristic.

The next render task is therefore concrete permutation attribution using
runtime draw evidence or an additional static discriminator that uniquely joins
one retail FXO program pair to the canonical material.
