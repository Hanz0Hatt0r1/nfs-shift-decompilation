---
name: d3d9-re
description: >-
  Reverse-engineer the SHIFT Direct3D 9 declaration, stream, shader and binding
  ABI using explicit static and runtime evidence chains.
---
# D3D9 reverse-engineering workflow

## Evidence layers

Keep static source/PE evidence, runtime capture and neutral backend contracts separate.

## Declaration ABI

`Stream:WORD, Offset:WORD, Type:BYTE, Method:BYTE, Usage:BYTE, UsageIndex:BYTE`

## BMW MEB bridge

- 460 → `[4,6,0]`
- 461 → `[4,6,1]`
- Type 4 → D3DDECLTYPE_D3DCOLOR
- Usage 6 → D3D9 COLOR (10)

This is a static mapping. Same-instance runtime proof remains separate.

## Runtime

Use draw-local capture snapshots to correlate MEB/resource identity, declaration, VB/IB, shader state and exact DrawIndexedPrimitive.

## RenderCommand

Carry accepted evidence into RenderCommand/1. Repacked VertexLayout offsets are target ABI, not original D3D9 offsets.

## Rule

Never fill missing Type/Usage/runtime identity with a plausible value.
