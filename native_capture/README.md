# SHIFT D3D9 capture producer

Windows-side research capture producer for the retail Direct3D 9 runtime.

The DLL is a small d3d9.dll proxy. It loads the system d3d9.dll, forwards
Direct3DCreate9, clones the returned COM vtables and patches only the D3D9
methods required by the Phase 152 evidence chain.

Captured events are JSONL and match SHIFT.D3D9RuntimeCaptureSchema/1.

## Captured methods

- CreateVertexDeclaration
- SetVertexDeclaration
- SetStreamSource
- SetIndices
- CreateVertexShader
- SetVertexShader
- SetVertexShaderConstantF
- CreatePixelShader
- SetPixelShader
- SetPixelShaderConstantF
- DrawIndexedPrimitive

Present is used only as a frame boundary; it is not emitted as an evidence
event. The frame counter advances after a successful present.

## Output

Set:

    SHIFT_D3D9_CAPTURE=shift_d3d9_capture.jsonl

The default is shift_d3d9_capture.jsonl in the process working directory.

The writer flushes every event by default so a crash still leaves a usable
prefix. Events include event_index, frame, thread_id and device_ptr.

The producer does not invent MEB identity. Engine-side resource identity and
the resource_sha256 correlation required by same_instance_gate remain a
separate Phase 153 hook.

## Build

Build on Windows with the normal MSVC toolchain:

    cmake -S native_capture -B native_capture/build -A Win32
    cmake --build native_capture/build --config Release

Place the resulting d3d9.dll next to the authorized test game's executable.
Run with:

    set SHIFT_D3D9_CAPTURE=C:\path\shift_d3d9_capture.jsonl

## Fail-closed behavior

Missing shader/declaration bytecode and unsuccessful D3D9 state changes are
not converted into inferred evidence. The Python capture schema and runtime
trace remain authoritative validation stages.
