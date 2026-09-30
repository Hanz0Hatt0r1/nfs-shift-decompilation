# Phase 565 — Silverstone FXO family inventory

Phase 565 extends the first native Silverstone slice from exact FX source
identity into the compiled D3D9 shader-cache corpus.

The production path is now:

`IMB → BMT → FX source → FXO cache family`.

## Inputs

The audit uses the same supplied Silverstone Era3 corpus plus the retail global
`RENDER.bff` used by Phase 564.

- `Silverstone_Era3_.zip`
  - SHA-256:
    `5423f5a0356e664a504f90c812e32bbbd4e2a0abe83c546fdc658305661a1e2f`
- `RENDER.bff`
  - SHA-256:
    `b0b03960ba7e620b7ad5e2b027ed13de67afffe168eb8b30da73c2a632a7c0af`

The five source shader references are the Phase 564 set:

- `render/shaders/basic_instanced.fx`;
- `render/shaders/crowd_geninstanced.fx`;
- `render/shaders/crowd_geninstanced_billboard.fx`;
- `render/shaders/foliage_instanced.fx`;
- `render/shaders/skintest_instanced.fx`.

## Source → cache-family identity

The audit reuses `render_pipeline.shader_family()`, which strips the
`render_shaders_` cache prefix and terminal hexadecimal cache identity before
normalization.

This is important because compiled permutations live mainly in the Silverstone
visual BFFs, not solely in `RENDER.bff`.

## Production result

Across the four visual Silverstone BFFs plus `RENDER.bff`:

| Family | FXO copies | Unique decoded payloads | Duplicate copies | Programs per copy |
|---|---:|---:|---:|---:|
| basic_instanced | 192 | 48 | 144 | 14 |
| crowd_geninstanced | 336 | 96 | 240 | 14 |
| crowd_geninstanced_billboard | 320 | 80 | 240 | 8 |
| foliage_instanced | 304 | 112 | 192 | 10 |
| skintest_instanced | 128 | 32 | 96 | 14 |
| **Total** | **1280** | **368** | **912** | — |

All 1280 candidate copies decode successfully through the canonical BFF
Type-2 XMem/LZX path and all candidate payloads contain parseable D3D9 shader
programs.

The decoded-content identity gate collapses 912 byte-identical duplicate
copies.

## Why this is not permutation closure

Every one of the five source families still has multiple distinct decoded FXO
payload identities. In addition, each payload contains multiple embedded shader
programs.

Therefore Phase 565 records:

- `inventory_ready = true`;
- `selection_ready = false`.

No FXO payload or VS/PS pair is selected by file ordering, archive ordering or
cache hash.

This is the same fail-closed principle already used for the BMW material path:
static evidence may narrow a target set, but tied identities are not converted
into a fabricated retail choice.

## Reusable audit

`tools/audit_shader_family_fxo.py` emits
`SHIFT.ShaderFamilyFXOInventory/1`.

Example:

```bash
python tools/audit_shader_family_fxo.py \
  Silverstone_Era3_.zip RENDER.bff \
  --dependency-evidence evidence/silverstone_era3_bmt_dependencies.json \
  -o out/silverstone-fxo-family-inventory.json \
  --require-inventory-ready
```

The audit:

1. resolves the requested source shader family;
2. scans matching FXO cache entries;
3. decodes each candidate through the BFF decoder;
4. parses embedded D3D9 programs;
5. collapses byte-identical decoded payloads by SHA-256;
6. reports ambiguity instead of selecting a permutation.

## Boundary

Phase 565 closes compiled-shader **inventory**, not compiled-shader
**attribution**.

The next vertical-slice gate is material-specific ranking of these 368 unique
payloads using the already implemented sampler, uniform, specialization,
vertex-interface and shader-pair evidence in `material_linker.link_material`.

Any tied top-rank permutation identities that survive that pass remain
runtime-capture targets rather than guessed selections.
