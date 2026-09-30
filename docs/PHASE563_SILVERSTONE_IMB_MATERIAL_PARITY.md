# Phase 563 — Silverstone IMB material-reference parity

Phase 563 closes the next scene-resource identity hop after Phase 562:

`IMB primitive material → MTX alias → same-archive BMT`.

## Production result

Across the supplied Silverstone Era3 visual corpus:

- 427 IMB resources;
- 428 primitive material references;
- 84 unique logical BMT references;
- 428 / 428 primitive references resolve to exactly one BMT in the same BFF;
- no missing same-archive material;
- no ambiguous same-archive material;
- every matched BMT entry uses BFF compression Type 2.

The one extra primitive relative to IMB count comes from the single two-primitive
IMB already identified in Phase 562.

Exact aggregate evidence is committed in
`evidence/silverstone_era3_imb_material_parity.json`.

## Alias rule

The retail IMB primitive names use `.mtx` references while the archive stores
the corresponding material payload as `.bmt`.

The audit applies only the already-established terminal alias:

`path/name.mtx → path/name.bmt`.

It does not perform basename-only matching or cross-directory guessing.

## Same-archive rule

A material is ready only when there is exactly one normalized BMT match in the
same BFF as the source IMB.

Duplicate copies of the same logical BMT across Silverstone variants are not an
ambiguity because each source IMB resolves inside its own archive. Across the
four visual variants, 47 logical materials occur in all four BFFs, 6 in three,
2 in two, and 29 in one.

## Reusable audit

`tools/audit_imb_material_parity.py` emits
`SHIFT.IMBMaterialReferenceParity/1` for BFF files or ZIP corpora.

Example:

```bash
python tools/audit_imb_material_parity.py \
  Silverstone_Era3_.zip \
  -o out/silverstone-imb-material-parity.json \
  --require-all-ready
```

The gate deliberately stops at BMT identity. It does not claim the BMT payload,
shader family, FXO permutation, textures or renderer-global resources are ready.

## Next

The next vertical-slice gate is to decode these same-archive BMT payloads and
audit their shader/texture dependencies against the track corpus plus global
render resources.
