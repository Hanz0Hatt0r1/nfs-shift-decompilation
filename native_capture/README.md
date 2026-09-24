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
- SetTexture
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

### Texture stage capture

The producer also records `IDirect3DDevice9::SetTexture` as
`set_texture` events with zero-based sampler `stage` and the bound
`texture_ptr`. A NULL pointer is preserved as an explicit unbind.

The hook uses vtable slot 65 and is used by the runtime shader selector to
require real s0/s3 object bindings for the BMW bodywork material.

### Texture resource descriptors

Each `set_texture` event now optionally includes best-effort resource metadata:
resource type, dimensions, format, pool and level count for 2D/cube textures
(and width/height/depth for volume textures). Descriptor failure never drops the
original bind event.

## Optional frame screenshots

Set `SHIFT_D3D9_CAPTURE_SCREENSHOT=1` to save the D3D9 backbuffer on successful
capture frames as `shift_d3d9_frame_<frame>.ppm`. Use
`SHIFT_D3D9_CAPTURE_SCREENSHOT_EVERY=N` to capture every Nth frame and
`SHIFT_D3D9_CAPTURE_SCREENSHOT_DIR` to choose the output directory.

The hook runs before `Present`, uses a system-memory surface and currently
supports A8R8G8B8, X8R8G8B8 and R5G6B5 backbuffers. Screenshot capture is
optional and failure is reported as a separate JSONL event; it does not change
normal D3D9 rendering behavior.

### Optional runtime texture-content snapshots

For render-target-backed 2D/cube textures, the producer can also try to save the
actual surface contents:

    set SHIFT_D3D9_CAPTURE_TEXTURE_CONTENTS=1
    set SHIFT_D3D9_CAPTURE_TEXTURE_DIR=C:\shift-capture\textures
    set SHIFT_D3D9_CAPTURE_TEXTURE_STAGES=0,3

Only stages selected by `SHIFT_D3D9_CAPTURE_TEXTURE_STAGES` are attempted.
The default is all stages. 2D textures are written as one PPM; cube textures
are written as six face PPMs. Unsupported/non-render-target resources simply
produce no snapshot and the original `set_texture` event remains intact.
The event records `resource_snapshot_paths` when a snapshot was captured.
