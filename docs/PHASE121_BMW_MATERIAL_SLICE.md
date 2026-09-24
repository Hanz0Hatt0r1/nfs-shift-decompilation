# Phase 121 — exact BMW material slice

`SHIFT.BMWMaterialSlice/1` reduces an exact `SHIFT.BMWRenderSlice/1` to one primitive
and its material/shader/resource contract.

The selector requires:

- `selection_status=unique`;
- unique VS/PS pair;
- linked `SHIFT.LinkedShaderPair/1`;
- resolved material record;
- explicit D3D9 sampler register for material textures;
- ready `RenderCommand/1` when a command is present.

An ambiguous or missing shader/material prerequisite remains a blocker.

## CLI

```bash
python shift_importer.py bmw-material-slice bmw-slice.json bmw-paint-slice.json --primitive-index 1
```

## Next

Feed the selected material slice into the desktop shader reference, compare sampler/constant
bindings to the linked shader IR, and produce the first deterministic BMW material image hash.