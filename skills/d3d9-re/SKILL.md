---
name: d3d9-re
description: >-
  Reverse-engineer the SHIFT Direct3D 9 declaration, stream, shader and binding
  ABI using explicit evidence chains. Use for D3D9 vtable calls, declaration
  records, Type/Usage tables, SetVertexDeclaration, SetStreamSource, SetIndices,
  shader registers, runtime capture correlation, parity validation, shader constants,
  and vertex-input semantic parity.
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
Use `d3d9_declaration_instance.py` for raw decoding and `bmw_vertex_input_parity.py`
for semantic checks against shader DCLs and the target VertexLayout.

## Shader constants

Runtime traces accept `set_vertex_shader_constant_f` and
`set_pixel_shader_constant_f` with exact float vectors. Value parity is optional during
exploration and can be made mandatory with `--require-constant-values`.

## MEB bridge

MEB binary descriptor triples are `[Type ordinal, Usage ordinal, Channel]`.
Runtime declarations contain D3D9 Type/Usage/UsageIndex bytes. A triple-level match
therefore requires an explicit Usage-ordinal map; the tooling intentionally refuses
to invent one.

## Vertex inputs

Semantic identity is taken from the shader `DCL` usage/index and the target
`VertexLayout/1` usage/index. A missing MEB Usage ordinal is a proof gap, not a reason
to invent a D3D9 Usage value. Repacked target offsets are not presented as original
runtime Stream/Offset values.

## Rendering boundary

Carry the same evidence into RenderCommand rather than reparsing or heuristically
remapping the original BFF at runtime.


## MEB descriptor triples

`SHIFT.BMWMEBDescriptorParity/1` validates preserved MEB descriptor bytes against their decoded `[Type, Usage, Channel]` words and the target `VertexLayout/1`. The raw 12-byte payload is checked as little-endian DWORDs before it participates in runtime declaration parity.


## Usage ordinal bridge

Use `meb_runtime_usage_bridge.py` to derive MEB Usage ordinals from exact same-resource runtime declaration records. The tool never invents missing Usage bytes and marks conflicting observations as `ambiguous`.


## Capture schema

`SHIFT.D3D9RuntimeCaptureSchema/1` is enforced by `d3d9_runtime_trace.load_events`. Use `validate-d3d9-capture` to validate a raw JSONL capture before semantic correlation. The schema checks structure only; resource identity, shader identity and Usage mappings remain separate evidence layers.


## RenderCommand constants

Use `render-command-constant-parity` to validate c-register ranges and 16-byte offsets between `MaterialUniformBinding/1`, `MaterialConstantPayload/1` and `RenderCommand/1`. The unified BMW gate runs this check automatically for constant-bearing commands.


## BMW paint material

Use `bmw_m3_paint_contract.py` to validate the documented M3 paint binding. The contract captures exact material sampler registers and renderer-global samplers without treating them as runtime proof.


## BMW paint binding adapter

`bmw_m3_paint_contract.py` accepts the current `compile_material()` output shape and normalizes it before validation against the documented BMW M3 paint contract.


## Paint contract enforcement

For the exact BMW M3 paint material, `compile_material()` invokes `SHIFT.BMWM3PaintMaterialContract/1`. Sampler registers/state, shader path, specialization flags and external samplers are fail-closed before StaticDraw readiness.


## BMW paint shader gate

`bmw_m3_paint_shader_gate.py` enforces unique exact FXO selection, VS/PS pair validity and permutation identity for the documented BMW M3 paint material. It is fail-closed and does not invent a shader permutation.


## BMW golden shader gate

For `vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx`, `bmw_golden_gate.py` requires `paint_shader_gate.ready == true` as well as the existing paint contract. Other materials are unaffected.
