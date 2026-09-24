---
name: d3d9-re
description: >-
  Reverse-engineer the SHIFT Direct3D 9 declaration, stream, shader and binding
  ABI using explicit evidence chains. Use for D3D9 vtable calls, declaration
  records, Type/Usage tables, SetVertexDeclaration, SetStreamSource, SetIndices,
  shader registers, runtime capture correlation, parity validation and shader constants.
---
# D3D9 reverse-engineering workflow

The project uses two layers:

- **static evidence**: recovered SHIFT.exe C source, D3D9 vtable identities,
  declaration record layout, Type/Usage profiles;
- **runtime evidence**: captured declaration instances, resource identities,
  shader objects, shader constant writes, stream bindings, and draw calls.

Never collapse these layers into a claim of same-instance execution without an
explicit pointer/resource/frame correlation.

## Declaration evidence

A declaration record is 8 bytes:
`Stream:WORD, Offset:WORD, Type:BYTE, Method:BYTE, Usage:BYTE, UsageIndex:BYTE`.
Use `d3d9_declaration_instance.py` for raw decoding and the BMW runtime parity gate
for currently evidenced semantic checks.

## Shader constants

Runtime traces accept `set_vertex_shader_constant_f` and
`set_pixel_shader_constant_f` with exact float vectors. Value parity is optional during
exploration and can be made mandatory with `--require-constant-values`.

## MEB bridge

MEB binary descriptor triples are `[Type ordinal, Usage ordinal, Channel]`.
Runtime declarations contain D3D9 Type/Usage/UsageIndex bytes. A triple-level match
therefore requires an explicit Usage-ordinal map; the tooling intentionally refuses
to invent one.

## Rendering boundary

Carry the same evidence into RenderCommand rather than reparsing or heuristically
remapping the original BFF at runtime.