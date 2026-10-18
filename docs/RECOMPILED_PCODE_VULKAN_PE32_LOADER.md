# Recompiled P-code PE32 guest image loading

The Linux Vulkan runtime can load an x86 PE32 image into the 32-bit guest RAM
used by the recompiled P-code module:

```bash
shift_runtime \
  --mesh scene.mgeo \
  --shader-dir native_runtime/build/shaders \
  --recompiled-module libnfs_shift_pcode.so \
  --pe-image SHIFT.exe \
  --recompiled-entrypoint
```

`--recompiled-entrypoint` invokes the PE entry point once before the frame loop.
The runtime seeds ESP, EBP, and a zero return slot for this call. Use
`--recompiled-step ADDRESS` separately when a selected guest function should run
on each native fixed step.

The loader checks the DOS and PE signatures, I386 machine type, PE32 optional
header, section table, image bounds, and non-overlapping mapped section ranges.
It maps headers at `ImageBase`, copies section raw bytes to `ImageBase + RVA`,
and leaves virtual section tails zero-filled. It reports the mapped base, image
size, entry point, and section count in the runtime JSON.

When the PE32 optional header contains an import directory, the loader reads
named and ordinal imports and rewrites each IAT slot to a unique guest address.
The runtime implements the observed Kernel32 subset reached by the retail
entry-point probe: `GetSystemTimeAsFileTime`, `GetCurrentProcessId`,
`GetCurrentThreadId`, `GetTickCount`, `QueryPerformanceCounter`,
`QueryPerformanceFrequency`, `GetStartupInfoA`, `GetProcessHeap`, `HeapCreate`,
`HeapAlloc`, `HeapFree`, `GetVersionExA`, `GetModuleHandleA`,
`GetModuleFileNameA`, and
`GetProcAddress`, `TlsAlloc`, `TlsGetValue`, `TlsSetValue`, `TlsFree`,
`InitializeCriticalSectionAndSpinCount`, `InterlockedIncrement`,
`InterlockedDecrement`,
`InitializeCriticalSection`, `EnterCriticalSection`, `TryEnterCriticalSection`,
`LeaveCriticalSection`, `DeleteCriticalSection`, and
`SetCriticalSectionSpinCount`, `GetStdHandle`, `GetFileType`, and
`SetHandleCount`, `GetCommandLineA`, `GetEnvironmentStringsW`,
`FreeEnvironmentStringsW`, `GetEnvironmentStrings`, and
`FreeEnvironmentStringsA`, `WideCharToMultiByte`, `GetLastError`, and
`SetLastError`, `GetACP`, `IsValidCodePage`, `GetCPInfo`, and
`GetStringTypeW`, `MultiByteToWideChar`, and `LCMapStringW`.
`GetStdHandle` returns
synthetic guest handles for stdin/stdout/stderr; those handles are not bridged to
host file descriptors. `GetFileType` classifies those three synthetic streams
as character devices and returns `FILE_TYPE_UNKNOWN` for other handles. The
ANSI command-line service returns a static guest string, `SHIFT.exe`, without
additional arguments. The environment block is currently empty in both ANSI
and UTF-16 forms; the corresponding free calls accept only the guest block
pointer. `MultiByteToWideChar` and `WideCharToMultiByte` convert Windows-1252
text; unsupported code pages and flags fail closed. The
last-error value is stored for the single guest thread, initially zero.
`GetACP` uses a fixed Windows-1252 profile for this startup path, and
`IsValidCodePage` admits only that configured code page.
`GetCPInfo` reports a one-byte character size, `?` as the default byte, and no
lead-byte ranges for Windows-1252.
`GetStringTypeW` provides deterministic restricted CTYPE1 classification for
the supported Windows-1252/Latin-1 range used by this CRT startup path.
`LCMapStringW` supports Windows-1252 lowercase and uppercase mappings.
clock APIs use the host system clock or monotonic clock; the performance counter
reports nanoseconds with a frequency of 1,000,000,000 ticks per second.
`GetStartupInfoA` returns a zeroed 68-byte
structure with `cb` set to 68 because this runtime has no Windows process
creation state. `GetProcessHeap` and `HeapCreate` return guest handles;
`HeapAlloc` reserves aligned ranges in guest RAM and `HeapFree` returns tracked
ranges for reuse. `HeapCreate` does not enforce its initial or maximum size.
`GetVersionExA` reports a Windows XP SP3
compatibility profile in either supported ANSI structure size; this is not a
Windows subsystem. `GetModuleHandleA(NULL)` returns the guest PE image base;
names present in the PE import table resolve to synthetic module handles.
`GetModuleFileNameA` returns the path supplied when loading the guest PE image;
its truncation behavior follows the reported Windows XP compatibility profile.
`GetProcAddress` resolves imported traps and can create traps for implemented
Kernel32 functions not present in the static import table; unknown symbols
return null. TLS slots are currently scoped to the single guest thread.
All implemented calls follow the x86 stdcall stack contract. Other imported
APIs still stop with an error naming the `DLL!function` or ordinal.
The tiny retail `TlsAlloc` wrapper thunk is recognized by its exact x86 import-
call/`ret 4` byte pattern and dispatches through the remapped IAT slot.

The module currently accepts one image-load attempt per guest address space and
loads only at the image's preferred base. The PE entry point runs only when
`--recompiled-entrypoint` is supplied; it is invoked once with a small synthetic
stack and does not establish complete Windows process state. The configured
P-code step is invoked separately by the native fixed-step loop. Most imported
APIs, multi-thread TLS and atomics, Windows process initialization, guest page
permissions, retail timing, and game startup are not implemented. A missing generated-function
export still fails closed unless it matches the documented TlsAlloc thunk.
The Vulkan scene and this P-code loop are therefore a runtime integration
probe, not a playable NFS Shift build.

The focused fixture test creates a small PE32 image and verifies header/section
mapping, zero-fill, all forty-six IAT mappings, the implemented Kernel32 outputs,
stdcall stack cleanup, null-pointer rejection, diagnostic import dispatch,
one-shot entry-point execution, duplicate-load rejection, and generated P-code
reads from guest memory. The Linux Vulkan CI smoke invokes the fixture entry
point once, runs the P-code read for three rendered frames, and checks that
Vulkan validation reports zero errors. Results are recorded in
[`evidence/recompiled_pcode_pe32_vulkan_runtime_20261018.json`](../evidence/recompiled_pcode_pe32_vulkan_runtime_20261018.json)
and
[`evidence/recompiled_pcode_pe32_import_boundary_20261018.json`](../evidence/recompiled_pcode_pe32_import_boundary_20261018.json).
The retail entry-point probe is recorded in
[`evidence/recompiled_pcode_kernel32_crt_startup_20261018.json`](../evidence/recompiled_pcode_kernel32_crt_startup_20261018.json).
