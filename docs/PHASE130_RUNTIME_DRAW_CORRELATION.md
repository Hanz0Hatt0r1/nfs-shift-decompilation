# Phase 130 — exact BMW runtime draw correlation

`SHIFT.BMWRuntimeDrawCorrelation/1` binds the selected BMW material primitive to
one concrete D3D9 indexed draw.

For the current static BMW mesh contract the comparison is:

- `first_index` == runtime `start_index`;
- `index_count / 3` == runtime `primitive_count`;
- the index range must be divisible by three (triangle-list contract).

One and only one runtime draw may match. Zero matches and multiple matches are
explicit blockers.

The result is consumed by `SHIFT.BMWRuntimeGoldenGate/1`, which already requires
shader/resource identity, sampler parity, constant parity, declaration parity,
trace integrity and ready `RenderCommand/1`.

## Why this closes a real gap

Matching a shader and MEB resource at frame level does not prove which of several
submeshes was drawn. The exact draw-range check ties the captured `DrawIndexedPrimitive`
to the same primitive selected by the offline BMW material slice.

## CLI

```bash
python shift_importer.py bmw-runtime-draw-correlation bmw-paint-slice.json runtime-evidence.json draw-correlation.json
```

## Next

Run the full golden gate on an actual runtime capture. Only a ready result may be
passed to `bmw-reference-render` and recorded as the first real-material image.