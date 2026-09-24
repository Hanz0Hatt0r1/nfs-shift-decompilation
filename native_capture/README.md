# SHIFT D3D9 capture proxy

`shift_d3d9_capture.dll` is a Windows-only, D3D9 vtable-capture helper for the
runtime evidence pipeline. It is intentionally small: it does not inject itself,
resolve BFF resources, or infer semantic mappings.

## Captured methods

- `CreateVertexDeclaration` / `SetVertexDeclaration`
- `CreateVertexShader` / `SetVertexShader`
- `CreatePixelShader` / `SetPixelShader`
- `SetVertexShaderConstantF` / `SetPixelShaderConstantF`
- `SetStreamSource` / `SetIndices`
- `DrawIndexedPrimitive`

Shader and declaration bytecode are emitted as `bytes_hex` with a bounded scan for
the D3D9 end token. Constant writes are emitted as float arrays.

## Host integration

1. Build on Windows with `cmake -S native_capture -B build/capture`.
2. Load the DLL into the target process by the project's chosen external injection/launcher path.
3. Call `ShiftD3D9TraceSetOutput(...)`.
4. Call `ShiftD3D9TraceInstall(device)` after a live `IDirect3DDevice9` exists.
5. Update `ShiftD3D9TraceSetFrame(...)` and optionally `ShiftD3D9TraceSetResource(...)` at the host's known frame/resource boundaries.
6. Call `ShiftD3D9TraceFlush()` before process teardown and `ShiftD3D9TraceShutdown()` to restore the original vtable.

## Evidence boundary

The proxy captures object pointers and bytes but does not claim same-instance
correlation with an offline MEB unless the host supplies `resource_path` /
`resource_sha256`. The Python `SHIFT.D3D9RuntimeTraceIntegrity/1` and
`SHIFT.BMWRuntimeGoldenGate/1` layers remain authoritative for acceptance.