# Phase 140 — BMW golden shader gate

`SHIFT.BMWGoldenRenderGate/1` now requires `SHIFT.BMWM3PaintShaderGate/1` for
the exact `vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx` primitive.

This closes a bypass where `paint_contract` could be ready while the underlying
FXO/VS/PS permutation evidence was missing or ambiguous.

## Exact M3 paint requirements

- `paint_contract.ready == true`;
- `paint_shader_gate.ready == true`;
- unique exact FXO selection;
- unique VS/PS pair;
- valid `SHIFT.ShaderPermutationIdentity/1`;
- exact material sampler registers and external sampler slots.

Other material references continue through the generic BMW golden gate without
requiring the M3-specific shader contract.

## Boundary

This is still offline/material-level evidence. A real runtime frame must separately
prove that the same resource, shader objects, declaration, constants and indexed draw
were used by the retail process.