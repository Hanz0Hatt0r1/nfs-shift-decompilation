# Phase 399 — BAR/BAR matrix coupling

`FUN_007bb6c0` fills the scalar lower-triangle matrix contributions for BAR constraints.

## Per-BAR self coefficient

For the current BAR, `p` is the point at `+0x18/+0x20/+0x28` and `q` is the direction at `+0x40/+0x48/+0x50`. The helper computes `c = p × q`, transforms `c` through `FUN_007aefb0(body +0xb0, c)`, and combines the transformed components with `q` and body `+0x90` to produce one scalar coefficient. It is added to `row_ptr[base][base]`, where `base` is BAR `+0x30`.

## BAR/BAR pair coefficient

For each later BAR, the source evaluates one scalar coefficient from the inner point/direction and the transformed outer cross product. Equal side flags (`+0x34`) add it; differing flags subtract it. The matrix cell is always stored in the lower triangle: row = `max(base_i, base_j)`, column = `min(base_i, base_j)`.

The source BAR sample stride is `0x60`, sample array base is `+0x168`, and inverse scalar is body `+0x90`.

This phase intentionally leaves JOINT/BAR and HINGE/BAR mixed-type coupling to their respective source helpers.
