# Phase 139 — BMW M3 paint shader gate

`SHIFT.BMWM3PaintShaderGate/1` is the strict shader-side gate for the documented
BMW M3 E36 paint material.

Before the material can be renderer-ready it requires:

- `shader_selection.status == unique`;
- an exact selected FXO candidate;
- unique VS/PS pair selection;
- a linked `SHIFT.LinkedShaderPair/1`;
- valid `SHIFT.ShaderPermutationIdentity/1` with a SHA-256 identity;
- the documented s1/s2/s4 sampler registers;
- the documented renderer-global s3/s0 samplers;
- no unresolved material textures.

`compile_material()` invokes this gate for the exact
`vehicles/BMW_M3_E36/BMW_M3_E36_PAINT.mtx` reference and carries the resulting
blockers into `StaticDraw/1`.

This intentionally does not invent or prefer an FXO permutation. A tied or
heuristically selected permutation remains blocked until the evidence makes the
selection unique.

## Boundary

Material-level uniqueness is still distinct from runtime-instance proof. The runtime
golden gate must independently join the captured shader objects, declaration, constants
and indexed draw to the same BMW resource.