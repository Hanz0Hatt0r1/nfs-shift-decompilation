# Process 1B — `SetUnhandledExceptionFilter` runtime-entry surface

The pinned PC retail 1.02 SQLite call inventory contains exactly three direct calls to `SetUnhandledExceptionFilter`:

```text
0x0090a5e6  __invoke_watson
0x0090a7ac  _abort
0x00916f56  ___report_gsfailure
```

The matching hash-pinned Ghidra C export contains exactly three `SetUnhandledExceptionFilter(...)` invocations, and every one is:

```c
SetUnhandledExceptionFilter((LPTOP_LEVEL_EXCEPTION_FILTER)0x0);
```

Therefore this API family registers no application callback entrypoint in the pinned image. In particular it cannot directly enter any exact P1B `HDVehicle+0x4330` carrier.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1b_hdvehicle_4330_unhandled_exception_filter_surface.py \
  /path/to/shift_ghidra.sqlite \
  /path/to/SHIFT.exe.c \
  --output evidence/p1b_hdvehicle_4330_unhandled_exception_filter_surface.json
```

The analyzer fails closed if either input hash changes, the physical callsite set changes, any call becomes indirect, the source occurrence count changes, or any source call is no longer the pinned NULL registration form.

## Gate

```text
SetUnhandledExceptionFilter surface complete = true
non-NULL filter registrations = 0
exact HDVehicle+0x4330 carrier filter = 0

runtime callback registration ruled out = false
indirect entry into carriers ruled out = false
generic function-pointer stores/copies ruled out = false
computed/encoded code pointers ruled out = false
manager+0x374 identity join complete = false
final 0x004b86cf rejection = false
P1.3 complete = false
provider count = 7
```

## Boundary

This does not close vectored exception handlers, signal handlers, arbitrary function-pointer storage, computed code pointers, or other callback registration mechanisms.
