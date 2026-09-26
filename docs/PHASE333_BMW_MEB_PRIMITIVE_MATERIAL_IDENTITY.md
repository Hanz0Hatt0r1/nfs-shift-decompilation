# Phase 333: BMW M3 MEB primitive material identity

This phase freezes the material-reference side of the real KIT00 body MEB.

## Verified facts

The six MEB primitives use five unique `.mtx` references. For each reference,
the corresponding same-directory `.bmt` path obtained by replacing the
extension is present exactly once in `BMW_M3_E36.bff`, and every matched entry
uses BFF compression type 2.

Verified pairs:

| MEB primitive | MEB `.mtx` | Retail BFF `.bmt` | Entry |
|---|---|---|---:|
| 0 | BMW_M3_E36_BADGING.mtx | bmw_m3_e36_badging.bmt | 862 |
| 1 | BMW_M3_E36_PAINT.mtx | bmw_m3_e36_paint.bmt | 858 |
| 2 | BMW_M3_E36_PAINT.mtx | bmw_m3_e36_paint.bmt | 858 |
| 3 | GENERIC_WINDOWS.mtx | generic_windows.bmt | 855 |
| 4 | GENERIC_GLOSS_BLACK.mtx | generic_gloss_black.bmt | 853 |
| 5 | BMW_M3_E36_LIGHTSGLASS.mtx | bmw_m3_e36_lightsglass.bmt | 850 |

The paint material is intentionally reused by two MEB primitives; this is
represented as one BMT identity with use count two.

## Gate

`bmw_meb_material_parity.py` emits
`SHIFT.BMWM3MEBPrimitiveMaterialParity/1`.

It fails closed on wrong MEB identity, duplicate/missing BMT paths, unexpected
BFF compression type, or a mismatch in the unique BMT reference set.

## Boundary

The BMT payload is not decoded by this phase. Shader selection, material
constants and texture dependencies remain the next layer.
