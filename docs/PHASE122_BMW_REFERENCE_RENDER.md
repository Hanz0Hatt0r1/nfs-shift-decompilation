# Phase 122 — BMW desktop reference render

`SHIFT.BMWReferenceRender/1` is a thin execution adapter over the existing desktop
reference renderer. It consumes only a ready `SHIFT.BMWMaterialSlice/1`, neutral MEB
mesh JSON and, for shader-reference mode, an explicit `SHIFT.ReferenceTexture/1`.

## Modes

- geometry mode executes the existing `SHIFT.RenderCommand/1` renderer and records the output SHA-256;
- shader-reference mode executes `render_textured_render_command` with the same command, sampler and constant contracts.

The adapter does not read BFF archives and does not invent shader constants or
texture resources.

## CLI

```bash
python shift_importer.py bmw-reference-render bmw-paint-slice.json body.json body.ppm --width 512 --height 512
python shift_importer.py bmw-reference-render bmw-paint-slice.json body.json body.ppm --shader-reference --texture-json diffuse.json
```

## Acceptance

The returned report includes the deterministic PPM SHA-256 and preserves the
underlying renderer result. The first real BMW golden image must be generated only
after the selected material has a unique FXO/VS/PS contract and a ready RenderCommand.