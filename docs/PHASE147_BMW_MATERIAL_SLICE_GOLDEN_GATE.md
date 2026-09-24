# Phase 147 — BMW material slice golden gate

`SHIFT.BMWMaterialSliceGoldenGate/1` validates one renderer-facing BMW material slice
against the exact M3 golden asset.

Unlike `SHIFT.BMWGoldenRenderGate/1`, this gate intentionally accepts a single selected
primitive. It therefore sits directly between `bmw-real-material-slice` and the desktop
reference renderer.

## Checks

- exact M3 golden resource path and SHA-256;
- exact selected primitive index, `first_index`, `index_count` and material ref;
- mesh vertex/triangle counts;
- ready M3 paint material contract;
- ready M3 paint shader gate;
- `SHIFT.RenderCommand/1` format and readiness.

The gate never relaxes the full-packet golden rules and never infers a primitive from
material ordering.

## CLI

```bash
python shift_importer.py bmw-material-slice-golden-gate \
  evidence/bmw_m3_e36_kit00_body_loda.golden.json \
  bmw-material-slice.json \
  slice-gate.json \
  --primitive-index 1
```

`bmw-real-material-slice` runs this gate automatically before returning `ready=true`.

## Boundary

This is still offline archived evidence. Runtime declaration/shader/draw correlation
remains a separate acceptance gate.