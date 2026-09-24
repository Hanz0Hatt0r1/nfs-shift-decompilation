# Phase 129 — runtime trace integrity

`SHIFT.D3D9RuntimeTraceIntegrity/1` validates that an external capture preserves the
ordered identity of declaration/shader objects and that each draw has the expected
state prerequisites.

## Checks

- `SetVertexDeclaration`, `SetVertexShader` and `SetPixelShader` must reference an
  object created earlier in the trace;
- reusing an object pointer with different captured bytes is a blocker;
- every indexed draw must have declaration, VS, PS, stream source and index binding;
- a capture without any draw remains `partial`.

The integrity report is attached to `SHIFT.D3D9RuntimeBindingEvidence/1`, and
`SHIFT.BMWRuntimeGoldenGate/1` requires global integrity `observed` before accepting
a runtime frame as golden.

## Source evidence

`SHIFT.D3D9ShaderConstantBindEvidence/1` is also exposed through the importer. The
recovered SHIFT wrappers map vertex `SetVertexShaderConstantF` to vtable offset
`0x178` and pixel `SetPixelShaderConstantF` to `0x1b4`.

## Next

Use one real capture with declaration, shader, stream/index, sampler and constant
events. The remaining work is capture execution and final BMW reference rendering.