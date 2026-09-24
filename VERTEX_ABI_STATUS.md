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
## Phase 28: vertex location collision guard

`build_vertex_input_locations()` now rejects two classes of silent ABI corruption: one D3D9 input register mapping to multiple target locations, and multiple shader registers mapping to the same target location. The resulting `location_collisions` and `unresolved` records remain machine-readable.
## Phase 41: COLOR0/COLOR1 evidence

`color_abi.py` now preserves the unresolved MEB 460/461 channel-order ambiguity as explicit RGBA and BGRA candidate interpretations. It records raw/candidate SHA-256, basic channel statistics and can compare both candidates against a known RGBA8 reference without selecting a winner.


## Phase 55: renderer treatment of 230..234

Properties `230..234` are now consumed by the deterministic reference renderer as the existing semantic `TEXCOORD0..4` family. The renderer does not reinterpret their 3-component payload as an exact D3D declaration; it only preserves the already-established semantic mapping. Mixed 130/230 families for the same TEXCOORD are rejected as an ABI collision.
