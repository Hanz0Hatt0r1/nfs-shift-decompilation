# Phase 568 — Silverstone runtime shader target set

Phase 567 proves that every one of the 428 supplied Silverstone IMB primitive
bindings reaches a valid static shader-ranking result, but every result remains
ambiguous.

Phase 568 converts those complete top-rank sets into a capture-oriented runtime
target contract instead of selecting a retail shader permutation.

## Contract

The new contract is:

`SHIFT.IMBRuntimeShaderTargetSet/1`

implemented in:

`src/scene/imb_runtime_shader_target_set.py`.

Its input is the full `SHIFT.IMBMaterialShaderRanking/1` report produced by
`tools/audit_imb_material_shader_ranking.py`.

The ranking audit now preserves the complete top-rank candidate set for every
primitive context. This is required because the previous compact
`ambiguous_candidates` field intentionally retained only a diagnostic subset
and was not sufficient for capture filtering.

## Identity policy

Each top-rank candidate is reduced to the strongest runtime-observable byte
identity that can be used without inventing a permutation:

1. exact permutation identity when the VS/PS pair is statically unique;
2. exact pair byte hash when the pair is unique;
3. pixel shader byte hash as a prefilter-only target;
4. vertex shader byte hash as a prefilter-only fallback.

A primitive is `capture_ready` only when its complete declared top-rank set is
present and every candidate contributes a usable byte-hash target.

`attribution_ready` is stricter: every retained target must already represent
a statically unique exact pair.

Neither state performs render admission and neither chooses a retail
permutation.

## Silverstone production result

The complete Silverstone Era3 ranking surface was regenerated from the supplied
visual BFF corpus plus retail `RENDER.bff`.

Result:

- 428 primitive bindings;
- 428 / 428 capture-ready bindings;
- 0 / 428 exact-pair-attribution-ready bindings;
- 51 unique global hash targets;
- all 51 are pixel-shader byte hashes;
- zero strong exact-pair targets at this stage.

The number of retained pixel targets per primitive is:

| Pixel targets | Primitive bindings |
|---:|---:|
| 5 | 175 |
| 6 | 156 |
| 10 | 73 |
| 15 | 24 |

This is narrower than the Phase 567 permutation-identity ambiguity widths,
because multiple statically distinct pair/permutation candidates share the same
pixel shader bytecode.

## Family target counts

| Shader family | Unique pixel hashes |
|---|---:|
| basic_instanced | 11 |
| crowd_geninstanced | 20 |
| crowd_geninstanced_billboard | 10 |
| foliage_instanced | 5 |
| skintest_instanced | 5 |

The five family sets are disjoint in this corpus, yielding 51 unique pixel
hashes globally.

## Frozen evidence

The compact production result is committed as:

`evidence/silverstone_era3_runtime_shader_targets.json`.

It records the full 51-hash whitelist, family membership, per-binding target
width distribution and readiness boundary.

The complete per-primitive target-set JSON is intentionally generated on demand
from the full ranking report rather than committed as a large derived artifact.

## Usage

Generate the full ranking report:

```bash
python tools/audit_imb_material_shader_ranking.py \
  Silverstone_Era3_.zip RENDER.bff \
  -o out/silverstone-ranking.json
```

Then build capture targets:

```bash
python src/scene/imb_runtime_shader_target_set.py \
  out/silverstone-ranking.json \
  out/silverstone-runtime-shader-targets.json
```

## Boundary

Phase 568 closes capture prefilter construction, not runtime attribution.

The target set is explicitly:

- `render_admission = false`;
- `selects_permutation = false`;
- complete enough to filter D3D9 shader observations for every Silverstone
  primitive;
- insufficient to select an exact VS/PS pair by static evidence alone.

## Next

The next shader step is to reuse the existing BMW capture pattern for the track
slice:

`raw D3D9 JSONL → 51-hash prefilter → draw-local runtime evidence → per-IMB
primitive same-instance shader match`.

Only a same-instance runtime match may promote one of the Phase 567/568
candidates to the concrete retail permutation.
