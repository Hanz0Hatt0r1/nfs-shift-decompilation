# SHIFT D3D9 capture producer

Windows-side research capture producer for the retail Direct3D 9 runtime.

## Captured API surface

- CreateVertexDeclaration / SetVertexDeclaration
- SetStreamSource / SetIndices
- CreateVertexBuffer / CreateIndexBuffer
- CreateVertexShader / SetVertexShader
- SetVertexShaderConstantF
- CreatePixelShader / SetPixelShader
- SetPixelShaderConstantF
- SetTexture
- CreateTexture / CreateCubeTexture
- DrawIndexedPrimitive

Present is a frame boundary.

## Extended evidence

Optional capture paths cover:

- texture LockRect/UnlockRect payloads;
- cube face × mip identity;
- VB/IB Lock/Unlock payloads;
- resource creation lifecycle;
- draw-local state snapshots.

Binary payloads are separate artifacts referenced by versioned events.

## Stability and black-screen diagnostics

The proxy has three startup modes selected with `SHIFT_D3D9_CAPTURE_MODE`:

- `passthrough` loads the real system `d3d9.dll`, forwards the retail D3D9 exports, writes startup diagnostics, and does **not** modify any COM vtable. Use this first when validating a new build.
- `diagnostic` additionally hooks only the device lifecycle boundary: `CreateDevice`, `TestCooperativeLevel`, `Reset`, `Present`, `BeginScene`, `EndScene`, and `Clear`. It does not hook resources, shaders, buffers, textures, or draws.
- `capture` is the full evidence mode and adds the existing resource/shader/draw hooks. This remains the default for compatibility with existing capture workflows.

The log is JSONL. Set an explicit path with:

```bat
set SHIFT_D3D9_CAPTURE=C:\\temp\\shift_d3d9_capture.jsonl
```

If no path is specified the proxy first uses `shift_d3d9_capture.jsonl` in the process working directory and falls back to the Windows temporary directory if that path is not writable. Set `SHIFT_D3D9_CAPTURE_DEBUG_OUTPUT=1` to mirror events to `OutputDebugStringA` for DebugView/WinDbg.

Recommended black-screen isolation sequence:

```bat
set SHIFT_D3D9_CAPTURE_MODE=passthrough
SHIFT.exe

set SHIFT_D3D9_CAPTURE_MODE=diagnostic
SHIFT.exe

set SHIFT_D3D9_CAPTURE_MODE=capture
SHIFT.exe
```

Under Wine, prefer the native proxy explicitly and set the same mode before
launching the game:

```bash
export WINEDLLOVERRIDES="d3d9=n,b"
export SHIFT_D3D9_CAPTURE="$PWD/shift_d3d9_capture.jsonl"

export SHIFT_D3D9_CAPTURE_MODE=passthrough
wine SHIFT.exe

# If passthrough is clean, advance to lifecycle diagnostics:
export SHIFT_D3D9_CAPTURE_MODE=diagnostic
wine SHIFT.exe

# Enable full resource/shader/draw capture only after diagnostic mode is clean:
export SHIFT_D3D9_CAPTURE_MODE=capture
wine SHIFT.exe
```

Remove or rotate the JSONL log between runs so each diagnosis corresponds to a
single launch.

Interpretation:

- failure in `passthrough` points to proxy loading/export/system-DLL forwarding rather than a capture hook;
- `passthrough` working but `diagnostic` failing points to D3D9 object/vtable lifecycle interception;
- `diagnostic` working but `capture` failing isolates the fault to resource/shader/draw capture;
- `create_device_result`, `reset_result`, `present_result`, and `test_cooperative_level` contain HRESULTs needed to distinguish device creation failure, device loss, reset failure, and rendering/capture problems.

The retail `SHIFT.exe` imports `Direct3DCreate9`, `D3DPERF_BeginEvent`, and `D3DPERF_EndEvent` from `d3d9.dll`. The proxy now explicitly forwards these and the rest of the documented D3DPERF surface, `Direct3DCreate9Ex`, `DebugSetLevel`, and `DebugSetMute`. Windows CI checks the export table and executes a passthrough smoke load against the real system D3D9 runtime.

For very noisy captures, `SHIFT_D3D9_DIAG_PRESENT_EVERY=N` controls periodic successful Present logging (default: every 300 calls); failed Present calls are always recorded.


### Crash context capture

The proxy also installs a lightweight vectored exception observer on the first
D3D9 entry point. It does not consume or recover exceptions; it only records
the first access violation whose instruction pointer is inside the main game
image, then returns `EXCEPTION_CONTINUE_SEARCH` so Wine/the game keeps its
normal crash behaviour.

By default the record is written to `shift_d3d9_crash.jsonl` next to the
capture log (when `SHIFT_D3D9_CAPTURE` contains a directory) or in the current
working directory. Override it with:

```bash
export SHIFT_D3D9_CRASH_LOG="$PWD/shift_d3d9_crash.jsonl"
```

Disable the observer with `SHIFT_D3D9_CRASH_DIAGNOSTICS=0`.

A crash record contains the exception/read-write address, EIP/EAX/EBX/ECX/EDX/
ESI/EDI/EBP/ESP, image-relative RVA, current proxy frame counter and up to 32
raw stack dwords. This is intended to localize null dereferences and recover
candidate game return addresses without attaching GDB.

Analyze it with:

```bash
python native_capture/analyze_proxy_crash.py shift_d3d9_crash.jsonl
```

Analyze a completed or failed startup log with:

```bash
python native_capture/analyze_proxy_log.py shift_d3d9_capture.jsonl
```

The analyzer reports a compact diagnosis such as `passthrough-forwarding-ok`,
`device-creation-failure`, `device-present-failure`, or
`d3d9-presentation-path-alive`, and names common D3D9 HRESULTs such as
`D3DERR_DEVICELOST`, `D3DERR_DEVICENOTRESET`, and `D3DERR_INVALIDCALL`.

## Build

```bash
cmake -S native_capture -B native_capture/build -A Win32
cmake --build native_capture/build --config Release
```

Place the resulting d3d9.dll beside the authorized test executable.

The Win32 proxy is linked against the static MSVC/MinGW runtime so the deployed
DLL does not require a modern Visual C++ redistributable to be installed in the
SHIFT/Wine environment.

## Evidence rules

The producer records runtime observations; it does not invent MEB identity.

Same-instance proof is a later correlation across MEB/resource SHA, declaration, buffers, shader objects, textures and exact draw index.

Runtime authenticity is provenance metadata, not an automatic truth claim.

## Linux alternative

apitrace tooling can extract unique BMW draw/resource instances and payloads without first producing a multi-gigabyte text dump.
