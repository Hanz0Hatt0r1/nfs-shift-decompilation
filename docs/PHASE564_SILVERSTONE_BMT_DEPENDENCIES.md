# Phase 564 — Silverstone BMT dependency closure

Phase 564 extends the first native track slice through decoded material
dependencies:

`IMB → MTX/BMT → shader source + textures`.

## Production corpus

The supplied `Silverstone_Era3_.zip` contains 84 unique logical BMT paths,
materialized as 239 archive-local BMT occurrences across the four visual track
variants.

All 239 occurrences decode through the repository-compatible BLMY material
tree without an error.

## Local dependency closure

Every decoded material has:

- exactly one shader-source reference;
- between two and four DDS texture references;
- all of its DDS references available in the same Silverstone BFF.

Aggregate result:

- 239 parsed BMT occurrences;
- 563 texture references;
- 120 unique texture paths;
- 563 / 563 same-archive texture references resolved;
- zero missing local textures.

This means the track-local material/texture side is no longer the blocker for
the Silverstone IMB vertical slice.

## Global shader boundary

The 239 BMT occurrences reduce to only five shader-source families:

- `render/shaders/basic_instanced.fx` — 114 uses;
- `render/shaders/crowd_geninstanced.fx` — 40 uses;
- `render/shaders/crowd_geninstanced_billboard.fx` — 44 uses;
- `render/shaders/foliage_instanced.fx` — 37 uses;
- `render/shaders/skintest_instanced.fx` — 4 uses.

None of those shader sources live inside the supplied Silverstone BFFs. They
are renderer-global dependencies, not missing track-local assets.

The dependency gate therefore distinguishes:

- **local_ready** — BMT parses and every texture resolves inside the same BFF;
- **ready** — local_ready plus an exact shader-source match among all supplied
  BFFs.

The Silverstone-only corpus is local-ready for all 239 materials and globally
blocked only by the five shader paths above.

## Reusable audit

`tools/audit_imb_material_dependencies.py` emits
`SHIFT.IMBMaterialDependencyAudit/1`.

Additional global archives can be supplied alongside the track ZIP. Shader
source lookup is exact-path across all supplied BFFs; texture lookup remains
strictly same-archive.

```bash
python tools/audit_imb_material_dependencies.py \
  Silverstone_Era3_.zip RENDER.bff \
  -o out/silverstone-material-deps.json \
  --require-all-ready
```

For a track-only audit:

```bash
python tools/audit_imb_material_dependencies.py \
  Silverstone_Era3_.zip \
  -o out/silverstone-local-material-deps.json \
  --require-local-ready
```

## Boundary

This phase does not select FXO permutations, translate shaders, provide
renderer-global textures, or prove native Vulkan output. It narrows the next
external dependency search to five exact FX source paths.
