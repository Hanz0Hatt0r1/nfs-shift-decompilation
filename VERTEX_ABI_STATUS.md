# SHIFT Vertex ABI status

## Phase 11

SHIFT.VertexLayout/1 now records ABI evidence explicitly instead of exposing only a storage descriptor.

### Evidence states

- `proven`: source representation and semantic contract are established by the current parser/runtime evidence.
- `inferred`: storage/width is established, but the exact original D3D9 declaration still needs direct declaration evidence.
- `ambiguous`: multiple source interpretations remain valid, and the renderer must not choose silently.
- `unknown`: the property is not yet decoded well enough for a render contract.

### Current BMW target state

| MEB | Semantic | Android storage | State |
|---|---|---|---|
| 200 | POSITION0 | FLOAT32x3 | inferred |
| 220 | NORMAL0 | FLOAT32x3 | inferred |
| 240 | TANGENT0 | FLOAT32x3 | inferred |
| 250 | BINORMAL0 | FLOAT32x3 | inferred |
| 130-134 | TEXCOORD0-4 | FLOAT32x2 | inferred |
| 230-234 | TEXCOORD0-4 family | FLOAT32x3 | inferred |
| 310 | BLENDWEIGHT0 | FLOAT32x4 | proven |
| 580 | BLENDINDICES0 | UINT8x4 | proven |
| 460/461 | COLOR0/1 | UINT8x4 normalized | ambiguous |
| 033 | unknown | RAW4 | unknown |

`460/461` remain the primary unresolved render ABI because the current evidence does not prove the original D3D9 declaration (`D3DCOLOR` vs `UBYTE4N`) or channel byte order (`RGBA` vs `BGRA`).

`SHIFT.StaticDraw/1` therefore blocks those attributes only when the selected shader binding actually consumes them.