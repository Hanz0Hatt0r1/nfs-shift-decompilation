# Phase 606 — runtime pipeline candidate join

## Goal

Use the compact Phase 603–605 runtime pipeline catalogue to narrow the static
Silverstone Phase 568 shader target surface before exact resource/same-instance
evidence is available.

This is deliberately a **candidate join**, not shader admission.

## Input contracts

The join consumes:

- `SHIFT.D3D9TargetDrawSignatureCatalog/1`;
- the full generated `SHIFT.IMBRuntimeShaderTargetSet/1`.

The compact production Phase 568 evidence file is not sufficient for this
step because it intentionally omits per-binding candidate variants.

## Pair matching

For every observed runtime pipeline signature the join uses the captured:

- vertex-shader byte SHA-256;
- pixel-shader byte SHA-256.

It indexes every preserved static `candidate_variant` by the same exact VS+PS
byte-hash pair and reports all primitive bindings containing that pair.

Each runtime pipeline is classified as:

- `single-static-binding-candidate`;
- `ambiguous-static-binding-candidates`;
- `pixel-only-static-overlap`;
- `no-static-pair-candidate`.

The result preserves static binding identity, IMB path/SHA, primitive index,
draw range, material/BMT identity, family, vertex properties and exact
candidate FXO/program offsets.

## Boundary

A single static candidate is **not** same-instance proof.

The current raw capture still lacks exact runtime IMB path/SHA and payload
identity, so this phase cannot authorize:

- resource identity;
- primitive identity;
- same-instance identity;
- shader admission;
- render admission.

Promotion remains behind the existing Phase 572 gates:

`exact runtime IMB identity + exact primitive draw range + strong shader
variant match`.

## Usage

First generate the full Phase 568 target set from a full material-ranking
report:

```bash
python src/scene/imb_runtime_shader_target_set.py \
  out/silverstone-material-shader-ranking.json \
  out/silverstone-runtime-shader-target-set.json
```

Then join the observed runtime pipelines:

```bash
python src/scene/imb_runtime_pipeline_candidate_join.py \
  out/d3d9_target_draw_signatures.json \
  out/silverstone-runtime-shader-target-set.json \
  out/d3d9_runtime_pipeline_candidate_join.json
```
