# Recompiled P-code PE32 guest image loading

The Linux Vulkan runtime can load an x86 PE32 image into the 32-bit guest RAM
used by the recompiled P-code module:

```bash
shift_runtime \
  --mesh scene.mgeo \
  --shader-dir native_runtime/build/shaders \
  --recompiled-module libnfs_shift_pcode.so \
  --recompiled-supplement libnfs_shift_startup_delta.so \
  --pe-image SHIFT.exe \
  --recompiled-entrypoint
```

`--recompiled-entrypoint` invokes the PE entry point once before the frame loop.
The runtime seeds ESP, EBP, and a zero return slot for this call. Use
`--recompiled-step ADDRESS` separately when a selected guest function should run
on each native fixed step.

Before the PE entry point, the guest receives the x86 FS base and a minimal TEB
at `0x7ffde000`: an empty exception-list sentinel, stack bounds, and the TEB
self pointer. Its x87 control, status, and tag words start at `0x037f`, `0`,
and `0xffff` respectively, matching `FNINIT`. This does not implement exception
dispatch or the rest of Windows thread/process startup.

Repeat `--recompiled-supplement ELF` to load additive P-code shards before guest
execution. Function lookup checks the primary module and then supplements;
duplicate exports fail closed. Supplements cannot be added after P-code
execution begins, so all modules are fixed before the PE entry point runs.
The loader also routes the lowered corpus's one-based static-import IDs to the
same guest import traps, and recognizes x86 `JMP [absolute]` thunks by reading
their target from guest memory.

The loader checks the DOS and PE signatures, I386 machine type, PE32 optional
header, section table, image bounds, and non-overlapping mapped section ranges.
It maps headers at `ImageBase`, copies section raw bytes to `ImageBase + RVA`,
and leaves virtual section tails zero-filled. It reports the mapped base, image
size, entry point, and section count in the runtime JSON.

When the PE32 optional header contains an import directory, the loader reads
named and ordinal imports and rewrites each IAT slot to a unique guest address.
The runtime implements the observed Kernel32 subset reached by the retail
entry-point probe: `GetSystemTimeAsFileTime`, `GetCurrentProcess`, `GetPriorityClass`, `GetCurrentProcessId`,
`GetCurrentThread`, `GetThreadPriority`, `SetPriorityClass`, `SetThreadPriority`,
`GetCurrentThreadId`, `GetTickCount`, `QueryPerformanceCounter`,
`QueryPerformanceFrequency`, `GetStartupInfoA`, `GetProcessHeap`, `CreateMutexA`,
`WaitForSingleObject`, `WaitForSingleObjectEx`, `CreateEventA`, `CreateEventW`,
`SetEvent`, `ResetEvent`, `InterlockedCompareExchange`, `VirtualAlloc`,
`VirtualFree`, `ReleaseMutex`,
`CloseHandle`, `CreateFileA`,
`GetFileSize`, `ReadFile`, `HeapCreate`,
`HeapAlloc`, `HeapSize`, `HeapFree`, `GetVersionExA`, `SetUnhandledExceptionFilter`,
`GetModuleHandleA`,
`GetModuleFileNameA`, and
`GetProcAddress`, `TlsAlloc`, `TlsGetValue`, `TlsSetValue`, `TlsFree`,
`InitializeCriticalSectionAndSpinCount`, `InterlockedIncrement`,
`InterlockedDecrement`,
`InitializeCriticalSection`, `EnterCriticalSection`, `TryEnterCriticalSection`,
`LeaveCriticalSection`, `DeleteCriticalSection`, and
`SetCriticalSectionSpinCount`, `GetStdHandle`, `GetFileType`, and
`SetHandleCount`, `GetCommandLineA`, `GetEnvironmentVariableA`,
`SetEnvironmentVariableA`,
`GetEnvironmentStringsW`,
`FreeEnvironmentStringsW`, `GetEnvironmentStrings`, and
`FreeEnvironmentStringsA`, `WideCharToMultiByte`, `GetLastError`, and
`SetLastError`, `GetACP`, `IsValidCodePage`, `GetCPInfo`, and
`GetStringTypeW`, `MultiByteToWideChar`, and `LCMapStringW`.
`WINMM.dll!timeBeginPeriod` and `timeEndPeriod` track matching single-thread
guest requests for the supported virtual 1 ms period; they do not change the
Linux host timer resolution. Other periods and unmatched end requests return
`TIMERR_NOCANDO`.
`GetStdHandle` returns
synthetic guest handles for stdin/stdout/stderr; those handles are not bridged to
host file descriptors. `GetFileType` classifies those three synthetic streams
as character devices and returns `FILE_TYPE_UNKNOWN` for other handles. The
process and thread priority APIs update one guest process/thread profile and
never change Linux host scheduling. Current process/thread pseudo-handles are
`0xFFFFFFFF` and `0xFFFFFFFE`; both priorities start at normal. The ANSI
command-line service returns a static guest string, `SHIFT.exe`, without
additional arguments. The guest environment starts empty; `SetEnvironmentVariableA`
adds, updates, or removes case-insensitive names, `GetEnvironmentVariableA`
reads them, and both environment-block APIs return caller-freed snapshots.
Missing names report `ERROR_ENVVAR_NOT_FOUND`. `MultiByteToWideChar` and
`WideCharToMultiByte` convert Windows-1252
text; unsupported code pages and flags fail closed. The
last-error value is stored for the single guest thread, initially zero.
`GetACP` uses a fixed Windows-1252 profile for this startup path, and
`IsValidCodePage` admits only that configured code page.
`GetCPInfo` reports a one-byte character size, `?` as the default byte, and no
lead-byte ranges for Windows-1252.
`GetStringTypeW` provides deterministic restricted CTYPE1 classification for
the supported Windows-1252/Latin-1 range used by this CRT startup path.
`LCMapStringW` supports Windows-1252 lowercase and uppercase mappings.
`CreateMutexA` returns synthetic handles and reuses a handle for a repeated
nonempty name within the guest process. `HeapSize` reports the tracked aligned
size of a live allocation and returns `SIZE_T(-1)` for invalid pointers.
`WaitForSingleObject` and `ReleaseMutex` model recursive ownership for these
mutexes in the single guest thread. `InterlockedCompareExchange` uses
single-thread guest memory semantics. Unnamed events support manual and auto-reset state;
an unsignaled zero-time wait returns `WAIT_TIMEOUT`, while an unsignaled
infinite wait fails closed because guest scheduling is single-threaded.
`WaitForSingleObjectEx` supports non-alertable waits. Named events and alertable
waits fail closed. `CloseHandle` closes
synthetic file, mutex, and event handles and rejects unknown handles. File
opens are limited to read-only `OPEN_EXISTING` paths within the runtime's
current working directory; writes, asynchronous I/O, and path traversal are
rejected. `SymSetOptions`, `SymInitialize`, and `SymCleanup` maintain a minimal
ImageHlp session; symbol and line lookups return no-symbol results.
`VirtualAlloc` returns zeroed guest RAM at a 64-KiB aligned synthetic address
starting at `0x20000000`, for regions up to 512 MiB. `VirtualFree` supports
`MEM_RELEASE` with size zero. Guest page protections and decommit are not
modeled.
`SetUnhandledExceptionFilter` stores the guest callback address and returns the
previous one; guest exceptions still fail closed and do not dispatch that
callback. The x86 CPUID P-code userops used by this image query the Linux host
CPU and write the four guest registers to guest RAM. `RDTSC` returns monotonic
nanosecond ticks as a virtual guest counter. `LOCK` and `UNLOCK` are no-ops for
the single-thread guest. Other userops still fail closed.
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
loads only at the image's preferred base. The fixed TEB page must not overlap
the loaded image; that configuration fails closed. Supplemental P-code ELFs are
additive function shards and do not add guest memory regions. The PE entry point
runs only when `--recompiled-entrypoint` is supplied; it is invoked once with a
synthetic stack and partial single-thread state. The configured P-code step is
invoked separately by the native fixed-step loop. Most imported APIs,
multi-thread TLS and atomics, remaining Windows process/thread state, guest page
permissions, retail timing, and game startup are not implemented. A missing generated-function
export still fails closed unless it matches the documented TlsAlloc thunk.
The Vulkan scene and this P-code loop are therefore a runtime integration
probe, not a playable NFS Shift build.

The focused fixture test creates a small PE32 image and verifies header/section
mapping, zero-fill, all 76 IAT mappings across Kernel32, ImageHlp, and WinMM,
the implemented import outputs,
stdcall stack cleanup, null-pointer rejection, diagnostic import dispatch,
one-shot entry-point execution from a supplemental module, rejection of late
supplement loading, duplicate-load rejection, and generated P-code reads from
guest memory. The Linux Vulkan CI smoke invokes the supplemental fixture entry
point once, runs the P-code read for three rendered frames, and checks that
Vulkan validation reports zero errors. Results are recorded in
[`evidence/recompiled_pcode_pe32_vulkan_runtime_20261018.json`](../evidence/recompiled_pcode_pe32_vulkan_runtime_20261018.json)
and
[`evidence/recompiled_pcode_pe32_import_boundary_20261018.json`](../evidence/recompiled_pcode_pe32_import_boundary_20261018.json).
The retail entry-point probe is recorded in
[`evidence/recompiled_pcode_kernel32_crt_startup_20261018.json`](../evidence/recompiled_pcode_kernel32_crt_startup_20261018.json).
