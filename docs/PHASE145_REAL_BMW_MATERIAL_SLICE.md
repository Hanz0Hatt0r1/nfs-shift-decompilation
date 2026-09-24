# Phase 145 — real BMW material slice

`bmw_real_material_slice.py` converts a real BFF-backed M3 paint binding into the existing
`SHIFT.BMWMaterialSlice/1` consumer format.

## Pipeline

`BMW_M3_E36.bff -> exact M3 BMT/MEB -> MaterialBinding/1 -> exact paint contract ->
exact shader gate -> StaticDraw/1 -> RenderResources/1 -> RenderCommand/1`.

The selected primitive defaults to index `1`, the first documented M3 paint range
(`first_index=150`, `index_count=6294`). Primitive `2` can be selected explicitly.

The output also contains the full neutral MEB JSON, so it can be passed directly to
`bmw_reference_render.py` once `ready=true`.

## CLI

```bash
python shift_importer.py bmw-real-material-slice \
  /path/BMW_M3_E36.bff \
  evidence/bmw_m3_e36_kit00_body_loda.golden.json \
  bmw-material-slice.json \
  --primitive-index 1 \
  --supplemental-bff /path/BMW_M3_E36_Cockpit.bff
```

Then:

```bash
python bmw_reference_render.py bmw-material-slice.json bmw-material-slice.json bmw.png
```

The second argument above must be replaced with the neutral MEB JSON contained in the
slice report when invoking the standalone renderer; the slice itself records both the
render command and the source mesh.

## Boundary

`ready=true` proves the archived offline render chain only. Runtime instance attribution
and capture authenticity are still separate gates.