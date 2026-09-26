# Phase 334: BMW M3 material dependency closure

This phase moves from primitive-to-BMT identity to the decoded material graph.

## Verified facts

The six body-MEB primitives reference five unique BMT materials. The decoded BMT
payloads resolve to:

| Material | Shader source | Texture dependencies |
|---|---|---|
| BMW_M3_E36_BADGING | `render/shaders/vehicles_basic.fx` | BADGING_DIFFUSE, BADGING_SPECULAR, BADGING_NORMALS |
| BMW_M3_E36_PAINT | `render/shaders/bodywork.fx` | COMMON_PAINT, COMMON_PAINT_SPECULAR, COMMON_BLANK |
| GENERIC_WINDOWS | `render/shaders/glass.fx` | COMMON_GLASS01_DIFFUSE, COMMON_BLANK, common_glass_cracks_01_normals |
| GENERIC_GLOSS_BLACK | `render/shaders/vehicles_basic.fx` | COMMON_BLACK, COMMON_WHITE |
| BMW_M3_E36_LIGHTSGLASS | `render/shaders/glass.fx` | BMW_M3_E36_LIGHTSGLASS_DIFFUSE, COMMON_BLANK, common_glass_cracks_01_normals |

All shader and texture paths referenced by these decoded BMTs were resolved in the
provided `BMW_M3_E36.bff` and `RENDER.bff` archives. No external resource was
needed for this closure.

The two PAINT MEB primitives intentionally share one decoded BMT identity.

## Gate

`bmw_m3_material_dependency_parity.py` emits
`SHIFT.BMWM3MaterialDependencyParity/1`.

It fails closed on wrong MEB identity, missing BMT payloads, BMT name mismatches,
or unresolved shader/texture references.

## Boundary

This phase proves resource/dependency closure only. It does not prove that the
shader compiles or reproduces the retail pixel output, and it does not provide
same-instance D3D9 draw attribution for every material resource.
