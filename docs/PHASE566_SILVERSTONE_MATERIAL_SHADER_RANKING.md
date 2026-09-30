# Phase 566 — material-specific Silverstone shader ranking audit

Phase 565 proves that the five Silverstone shader families are present in the
compiled FXO cache corpus and parse cleanly, but family identity alone leaves
368 distinct decoded payloads.

Phase 566 adds the next fail-closed narrowing stage:

`tools/audit_imb_material_shader_ranking.py`

which emits:

`SHIFT.IMBMaterialShaderRanking/1`.

## Ranking scope

Ranking is performed per concrete IMB primitive context, not per BMT filename.

The evidence tuple is:

`IMB primitive + IMB vertex properties + same-archive BMT + exact FX source + deduplicated same-family FXO payloads`.

This matters because the same material can be reused by geometry with different
vertex declarations, and the existing shader-pair validator uses the concrete
vertex property set.

## Existing ranking engine

The audit deliberately reuses `material_linker.link_material()` instead of
introducing a second shader-selection heuristic.

That ranking already combines:

- exact source sampler use;
- BMT texture parameter bindings;
- D3D9 CTAB sampler registers;
- reflected numeric constants;
- material uniform coverage;
- source-derived specialization indicators;
- VS→PS interface compatibility;
- concrete vertex-format compatibility;
- permutation / VS+PS byte identities.

## Content deduplication

Before ranking, every target FXO family is decoded through the BFF XMem/LZX
path and byte-identical decoded payloads are collapsed by SHA-256.

The filename or archive order is never used as evidence.

## Output gates

Each primitive binding is classified with the existing material-linker
selection state:

- `unique`: one evidence-backed top-ranked shader identity;
- `ambiguous`: multiple distinct tied identities or an ambiguous VS pair;
- `heuristic`: a best candidate exists but the vertex pair is not fully valid;
- `none`: no admissible candidate.

Only `unique` is counted as statically shader-selected.

`ambiguous`, `heuristic` and `none` rows remain runtime targets.

Unresolved textures and other upstream blockers are also preserved even when a
shader identity is unique.

## Context cache

The expensive linker pass is cached by:

`(archive, decoded BMT SHA-256, decoded FX-source SHA-256, vertex property tuple, shader family)`.

This avoids re-ranking identical material/geometry contexts while retaining all
428 primitive occurrences in the final report.

## Example

```bash
python tools/audit_imb_material_shader_ranking.py \
  Silverstone_Era3_.zip RENDER.bff \
  -o out/silverstone-material-shader-ranking.json
```

To make unresolved shader attribution fail the command:

```bash
python tools/audit_imb_material_shader_ranking.py \
  Silverstone_Era3_.zip RENDER.bff \
  -o out/silverstone-material-shader-ranking.json \
  --require-selection-ready
```

## Boundary

Phase 566 implements the reproducible ranking stage. It does not claim a
production Silverstone permutation result until the complete supplied corpus
has been executed through this new audit.

The next gate is to run the full corpus, freeze the counts/identities, and turn
any tied top-rank rows into explicit D3D9 runtime shader targets instead of
selecting them by convention.
