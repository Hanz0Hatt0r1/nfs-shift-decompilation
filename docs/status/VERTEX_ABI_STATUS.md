# SHIFT Vertex ABI status

## Layering

Keep separate:

1. MEB descriptor/source evidence;
2. D3D9 declaration/runtime evidence;
3. neutral VertexLayout/GLES/Vulkan target ABI.

Repacked target offsets are never presented as original D3D9 stream offsets.

## BMW mappings

| MEB property | Semantic | Storage |
|---:|---|---|
| 200 | POSITION0 | FLOAT32x3 |
| 220 | NORMAL0 | FLOAT32x3 |
| 240 | TANGENT0 | FLOAT32x3 |
| 250 | BINORMAL0 | FLOAT32x3 |
| 130..134 | TEXCOORD0..4 | FLOAT32x2 |
| 230..234 | TEXCOORD0..4 alternate | FLOAT32x3 |
| 310 | BLENDWEIGHT0 | FLOAT32x4 |
| 580 | BLENDINDICES0 | UINT8x4 |
| 460 | COLOR0 | Type-4 D3D9 packed-color path |
| 461 | COLOR1 | Type-4 D3D9 packed-color path when present |

## COLOR closure

Exact MEB descriptors:

`460 → [4,6,0]`
`461 → [4,6,1]`

Recovered executable tables:

`Type 4 = D3DDECLTYPE_D3DCOLOR`
`Usage 6 = D3D9 Usage 10 (COLOR)`

The supplied 1.02 corpus contains 70,370 property-460 instances with the exact descriptor. Property 461 is absent from that corpus.

Static ABI mapping is therefore resolved. Remaining proof is runtime same-instance attribution.

## Declaration record

Runtime declaration records are the 8-byte tuple:

`Stream:WORD, Offset:WORD, Type:BYTE, Method:BYTE, Usage:BYTE, UsageIndex:BYTE`

Creation, canonicalization, binding and D3DDECL_END evidence are represented separately.

## Runtime gate

Use draw-local snapshots to correlate declaration, stream/index, shader, constant and texture state at the exact DrawIndexedPrimitive.

## Status model

Evidence states remain machine-readable and fail-closed.
