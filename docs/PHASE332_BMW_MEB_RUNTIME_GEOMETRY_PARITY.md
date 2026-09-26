# Phase 332: BMW M3 MEB runtime geometry parity

This phase freezes the first repository-visible runtime geometry correlation for the
real BMW M3 E36 KIT00 body MEB.

## Verified facts

- Resource: `vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb`
- SHA-256: `960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c`
- Decoded size: 300,764 bytes
- Vertex count: 3,550
- Source index count: 15,102
- Source triangle count: 5,034
- Runtime vertex stride: 76 bytes
- Derived runtime VB size: 269,800 bytes
- Derived uint16 IB size: 30,204 bytes

The supplied frame-30444 geometry dump contains 28 draws satisfying the geometry
predicates `D3DPT_TRIANGLELIST`, `BaseVertexIndex=0`, `startIndex=0`,
`NumVertices=3550`, and `Stride=76`. All are bound to one runtime vertex
buffer address, `0x27b39460`.

The six MEB primitive triangle counts are all observed against that same vertex
buffer with distinct index-buffer bindings:

| Primitive | Material | Triangles | Runtime IB |
|---|---|---:|---|
| 0 | BADGING | 50 | `0x27b394e0` |
| 1 | PAINT | 2,098 | `0x27b395e0` |
| 2 | PAINT | 2,462 | `0x27b39560` |
| 3 | GENERIC_WINDOWS | 204 | `0x27b39660` |
| 4 | GENERIC_GLOSS_BLACK | 192 | `0x27b396e0` |
| 5 | LIGHTSGLASS | 28 | `0x27b39760` |

Observed histogram: `28:2, 50:6, 192:6, 204:2, 2098:6, 2462:6`.

## Gate

`bmw_meb_runtime_geometry_parity.py` emits
`SHIFT.BMWM3MEBRuntimeGeometryParity/1` and fails closed unless resource identity,
VB dimensions, primitive totals, primitive coverage, one common runtime VB and unique
per-primitive runtime IB bindings all agree.

Optional repacked VB/IB artifacts are checked by exact size and SHA-256. They are
repacked MEB artifacts, not claims of raw D3D9 runtime byte capture.

## Boundary

This phase does not close the strict same-instance shader/material proof gate.
Declaration, VS/PS, constants, samplers and their exact same-draw relationship remain
separate runtime evidence.
