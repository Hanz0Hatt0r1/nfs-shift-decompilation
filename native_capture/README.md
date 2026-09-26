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
- CreateTexture
- CreateCubeTexture
- CreateVertexBuffer
- CreateIndexBuffer
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
### Texture snapshot defaults

When `SHIFT_D3D9_CAPTURE_TEXTURE_SNAPSHOT=1` is enabled and no explicit
`SHIFT_D3D9_CAPTURE_TEXTURE_STAGES` is supplied, the producer now captures
all BMW paint sampler stages `s0..s4`. This includes the material-owned
diffuse/specular stages s1/s2 as well as the renderer-global s0/s3 and the
scratch-control s4.

Use `SHIFT_D3D9_CAPTURE_TEXTURE_STAGES` to narrow the set for diagnostic runs.


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

### Proxy startup diagnostics

The first call through the local proxy emits a `proxy_direct3dcreate9` event. A failed system-runtime load emits `proxy_system_d3d9_load_failed`; a successful system-runtime load emits `proxy_system_d3d9_ready`. These events distinguish a missing/unused proxy from a later capture failure.

For PortProton/Wine, force the local native proxy with:

    WINEDLLOVERRIDES="d3d9=n"

For the first diagnostic run, leave screenshot and texture snapshots disabled and inspect the JSONL event counts after the game starts. If no JSONL file is created, the next diagnostic is Wine DLL-load tracing with `WINEDEBUG=+loaddll`.

### Linux → Windows (32-bit) cross-build

On Linux, do not use the `MinGW Makefiles` generator. That generator is only
available when CMake itself is running on Windows. Use Ninja (or Unix Makefiles)
with the supplied i686 MinGW toolchain:

    cmake -S native_capture -B native_capture/build-mingw \
      -G Ninja \
      -DCMAKE_TOOLCHAIN_FILE=native_capture/toolchains/mingw-i686.cmake

    cmake --build native_capture/build-mingw -j"$(nproc)"

The resulting proxy is:

    native_capture/build-mingw/d3d9.dll

Check that the DLL is a 32-bit PE and that the MinGW runtime is not a DLL
dependency:

    file native_capture/build-mingw/d3d9.dll
    objdump -p native_capture/build-mingw/d3d9.dll | grep -Ei 'libgcc|libstdc|winpthread'

The second command should produce no matches.

The cross compiler must be installed as `i686-w64-mingw32-g++`. On
Debian/Ubuntu this is normally provided by the `g++-mingw-w64-i686` package.


### Texture object lifecycle

Successful `IDirect3DDevice9::CreateTexture` and
`CreateCubeTexture` calls are emitted with the returned texture pointer and
creation metadata. The Python runtime trace joins these events to later
`set_texture` bindings in event order.

This establishes the runtime pointer -> D3D9 creation-instance boundary. It
does not identify the original SHIFT DDS archive resource by itself; that
identity still requires resource-content evidence.


### Optional raw texture payload capture

Set `SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS=1` to capture write-side
`IDirect3DTexture9::LockRect/UnlockRect` payloads for all requested mip levels into separate binary files.
The JSONL stream emits `texture_payload` with the texture pointer, dimensions,
pitch, D3D format, byte count, level and file path. The capture is limited to
full-surface locks (`pRect == NULL`); sub-rectangle locks are not treated as a
complete mip level.

Set `SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOAD_DIR` to choose the payload directory.

Payload capture is intentionally opt-in because managed-texture uploads can
be numerous. The current hook covers 2D `IDirect3DTexture9` objects and writes
the locked memory before the original `UnlockRect` call invalidates it.

This is a raw texture surface payload, not a DDS file header. It is therefore
suitable for level-by-level comparison with the decoded archive DDS mip chain.

### Cube texture raw payload capture

When SHIFT_D3D9_CAPTURE_TEXTURE_PAYLOADS=1 is enabled, successful
write-side IDirect3DCubeTexture9::LockRect(face, level, ...) calls are captured with the same
texture_payload event used by 2D textures. Cube records additionally carry
face and face_name (px/nx/py/ny/pz/nz).

The cube lock state is keyed by texture object, face and mip level. This preserves
independent face/mip uploads and prevents one cube face from overwriting another
in-flight lock.

Cube payload capture is subject to the same full-surface rule: sub-rectangle and
read-only locks are not promoted to complete surface evidence. Render-target cube
textures in D3DPOOL_DEFAULT remain dependent on the existing face-level PPM
readback path when LockRect is unavailable.
    
### Buffer object lifecycle

Successful `CreateVertexBuffer` and `CreateIndexBuffer` calls are emitted with
the returned D3D9 buffer pointer and creation size/format metadata. The runtime
trace joins later stream/index bindings to the observed creation instance.

The current producer does not capture raw VB/IB bytes yet. This lifecycle event is
the prerequisite for a future lock/payload comparison against reconstructed MEB
vertex and INDEX16 data.

    
### Optional raw vertex/index buffer payload capture

Set `SHIFT_D3D9_CAPTURE_BUFFER_PAYLOADS=1` to capture full-surface
`IDirect3DVertexBuffer9::Lock/Unlock` and
`IDirect3DIndexBuffer9::Lock/Unlock` contents into standalone binary files.

Set `SHIFT_D3D9_CAPTURE_BUFFER_PAYLOAD_DIR` to select the output directory.

Only locks with offset 0 and size 0 (whole buffer) or size equal to the queried
buffer length are promoted to full-buffer payload evidence. The lock must also
have a successful `GetDesc`. Partial locks and descriptor failures are not
treated as complete VB/IB payloads.

The payload is copied before the original Unlock call invalidates the lock
pointer. JSONL emits a `buffer_payload` event with buffer pointer, kind,
requested/full sizes, flags and payload path.

The capture is opt-in because particle and dynamic mesh buffers can be large.
