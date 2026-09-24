# Phase 119 — resource identity propagation

Phase 119 closes an integrity gap exposed by the strict BMW golden gate: the render pipeline previously preserved only a resource path/archive pair. A path is not a content identity.

## Implemented

- `draw_packets.py` now carries `resource_sha256` and `resource_size` when the source analysis record provides `sha256` or `resource_sha256`.
- `render_pipeline.py` propagates the decoded MEB `sha256` into the `RenderBinding/1` mesh reference.
- `SHIFT.BMWGoldenRenderGate/1` requires the golden resource SHA-256 to be present and equal before a packet can be accepted.
- Regression coverage verifies that resource identity is preserved in the render-facing packet.

## Why this matters

The BMW golden manifest identifies the exact selected MEB by SHA-256. The renderer must preserve the same identity through `MEB -> DrawPacket/1 -> StaticDraw/1 -> RenderCommand/1`; otherwise a path-only collision or unintended replacement could look valid.

## Next

The next step is the real BMW material slice: resolve one selected primitive's `.mtx/.bmt`, FX source, FXO candidates, sampler registers, shader pair and material constants into one render command, then compile-check the linked GLSL and produce the first deterministic BMW image hash.