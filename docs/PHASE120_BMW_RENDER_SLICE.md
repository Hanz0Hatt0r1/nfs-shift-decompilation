# Phase 120 — exact BMW render slice

`SHIFT.BMWRenderSlice/1` is the deterministic bridge from a generic
`SHIFT.RenderBinding/1` report to the selected BMW M3 golden asset.

Selection requires both:

- normalized resource path equality;
- exact resource SHA-256 equality.

The selected packet is returned together with the corresponding `StaticDraw/1` and
`RenderCommand/1` entries by the same packet index. A path-only match, SHA-only match
or conflicting identity remains a blocker.

## CLI

```bash
python shift_importer.py bmw-render-slice evidence/bmw_m3_e36_kit00_body_loda.golden.json render-bindings.json bmw-slice.json
```

## Next

Run the selected real M3 slice through the material linker, prove a unique FXO
permutation, preserve material constants/samplers and generate the first desktop
golden image.