# Process 1D — Controller #1 loader reachability

The pinned retail SQLite contains 37 direct calls to `GetModuleHandleA/W`, `LoadLibraryA/W`, or `FreeLibrary`. Seven are directly reachable from Controller #1 worker `FUN_00662880`: six `GetModuleHandleA` and one `LoadLibraryA`.

Their local string contexts are limited to already bounded CLR/CRT/KERNEL32/USER32 resolver families: `CorExitProcess` / `mscoree.dll`, `.mixcrt`, `EncodePointer`, `DecodePointer`, `InitializeCriticalSectionAndSpinCount`, and USER32 helpers (`GetUserObjectInformationA`, `GetLastActivePopup`, `GetActiveWindow`, `MessageBoxA`). No APC/native queue name appears in the reachable loader contexts.

This closes only the direct loader/module-handle navigation surface. It does not rule out nonlocal argument flow, manual or hashed export resolution, indirect calls, callbacks, pre-resolved pointers, PEB/LDR walking, direct syscalls, or target-thread ambiguity.

Reproduce with:

```text
python3 tools/ghidra/analyze_p1d_controller1_loader_reachability.py \
  out/shift_ghidra.sqlite \
  --output out/p1d_controller1_loader_reachability.json
```

Gate remains fail-closed: Controller #1 timing exhaustive=false, P1.3D=false, provider count=7. Continue with #1699/#1712 native/manual primitive adjudication.
