# Phase 152 — D3D9 runtime capture producer

## Goal

Produce authentic D3D9 JSONL runtime evidence from a retail SHIFT process so
the existing Python parity and golden gates can consume an actual frame.

## Implemented boundary

native_capture/shift_d3d9_capture.cpp provides a Windows-only d3d9.dll proxy.
It:

1. loads the system D3D9 implementation;
2. forwards Direct3DCreate9;
3. clones the returned IDirect3D9 vtable and intercepts CreateDevice;
4. clones each created IDirect3DDevice9 vtable;
5. captures declaration and shader creation, state binds, stream/index state,
   shader constant writes and indexed draws;
6. uses successful Present calls as frame boundaries;
7. emits append-only JSONL with event sequence, frame, thread and device metadata.

The project evidence anchors for the captured D3D9 methods are:

- CreateVertexDeclaration: 0x158
- SetVertexDeclaration: 0x15c
- SetVertexShader: 0x170
- SetVertexShaderConstantF: 0x178
- SetStreamSource: 0x190
- SetIndices: 0x1a0
- DrawIndexedPrimitive: 0x148
- SetPixelShader: 0x1ac
- SetPixelShaderConstantF: 0x1b4

## Deliberate limits

The producer does not claim MEB identity. D3D9 exposes object pointers, not
SHIFT resource paths. Therefore resource_path and resource_sha256 are not
fabricated.

The producer also does not infer declaration Type/Usage/UsageIndex, material
sampler mapping or engine-side resource selection. Those remain downstream
evidence joins, with engine-side resource identity scheduled for Phase 153.

## Validation

d3d9_capture_schema.py now validates producer metadata, monotonic event_index
when supplied, non-regressing integer frames, and finite constant vectors.
Regression coverage exercises a complete producer-shaped event sequence,
sequence gaps, negative frames and non-finite values.

## Acceptance

Phase 152 is complete at source level when the Windows producer builds as a
d3d9.dll shared library and its emitted JSONL is accepted by
validate-d3d9-capture. A real retail capture is not generated in CI because it
requires an authorized Windows game runtime.

The next step is Phase 153: attach the SHIFT engine's MEB/resource identity to
the D3D9 vertex-buffer/declaration state so same_instance_gate can be proven
for an actual BMW M3 draw.
