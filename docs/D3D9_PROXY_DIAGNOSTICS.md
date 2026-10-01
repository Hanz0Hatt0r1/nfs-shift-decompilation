# D3D9 proxy black-screen diagnostics

The capture DLL is a forwarding proxy, not a replacement renderer. Its first
job is to preserve the D3D9 backend that the game would have used without the
capture layer.

## Backend selection

The proxy selects its real backend in this order:

1. `SHIFT_D3D9_BACKEND`, when explicitly set;
2. `d3d9.shift_backend.dll` beside the proxy;
3. the system/Wine `d3d9.dll`.

The selected source and path are emitted as
`proxy_d3d9_backend_selected`. A backend path that resolves back to the proxy
is rejected instead of recursing.

Both launch helpers preserve an existing game-local `d3d9.dll` by staging it
as `d3d9.shift_backend.dll` for the duration of the run and restoring the
original files afterwards. This is important for DXVK or any other local D3D9
implementation: installing the logger must not silently change the renderer.

## Staged diagnosis

Start with `diagnostic`. It only hooks D3D9 lifecycle calls needed to answer
whether device creation, reset and presentation are working. Move to full
`capture` only after that path is healthy.

Linux/Wine:

```bash
bash tools/run_shift_capture_wine.sh \
  --game /path/to/SHIFT.exe \
  --proxy /path/to/build/d3d9.dll \
  --output out/d3d9-diagnostic \
  --mode diagnostic
```

The Wine launcher forces native-first loading for the top-level `d3d9.dll`
proxy with `WINEDLLOVERRIDES=d3d9=n,b`. A pre-existing override string is
preserved after that entry.

Windows PowerShell:

```powershell
.\tools\run_shift_capture.ps1 `
  -GameExe C:\Games\SHIFT\SHIFT.exe `
  -ProxyDll C:\build\d3d9.dll `
  -OutputDir .\out\d3d9-diagnostic `
  -Mode Diagnostic
```

For a pure forwarding check use `passthrough`; this does not modify COM
vtables. For full shader/resource/draw evidence use `capture`.

## Reading the result

Run:

```bash
python native_capture/analyze_proxy_log.py out/d3d9-diagnostic/shift_d3d9_capture.jsonl
```

The analyzer distinguishes:

- backend load or required-export failure;
- proxy/vtable hook installation failure;
- `Direct3DCreate9` and `CreateDevice` failure;
- reset/cooperative-level failure;
- persistent `Present` failure;
- a live presentation path with at least one successful `Present`.

The backend source is included in the summary. If `diagnostic` works but
`capture` does not, the fault is narrowed to the additional resource/shader
hook surface rather than D3D9 forwarding or backend selection.

## Evidence boundary

A successful diagnostic run proves only that the proxy preserves a usable D3D9
creation/presentation path. It does not by itself prove shader/resource
same-instance attribution or renderer parity.
