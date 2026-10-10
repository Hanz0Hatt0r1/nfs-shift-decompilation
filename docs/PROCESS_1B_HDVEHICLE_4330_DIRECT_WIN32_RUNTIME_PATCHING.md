# Process 1B: direct Win32 runtime-patching surface

## Scope

This contract bounds only retail-image references to the standard Win32 APIs that can directly make code pages writable/executable or write another process, plus direct calls to the imported `VirtualAlloc`.

Authority: PC retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`, 8,801,792 bytes.

## Import surface

The PE has 26 import descriptors and 411 imported functions.

The following patch/protection APIs are not imported and their ASCII names do not occur in the retail image:

- `VirtualProtect`
- `VirtualProtectEx`
- `WriteProcessMemory`
- `FlushInstructionCache`
- `VirtualAllocEx`
- `NtProtectVirtualMemory`
- `ZwProtectVirtualMemory`

`VirtualAlloc` is imported through IAT slot `0x00aa6288`. That IAT address occurs exactly eight times in the whole retail image; all eight occurrences are direct `FF 15 [0x00aa6288]` calls, so there is no additional static reference/copy of this IAT slot.

All eight direct calls pass `flProtect = 0x04` (`PAGE_READWRITE`):

| Callsite | `flProtect` |
| --- | --- |
| `0x006344d2` | `0x04` |
| `0x0090ebf6` | `0x04` |
| `0x0090ec81` | `0x04` |
| `0x00a5cac1` | `0x04` |
| `0x00a5cafc` | `0x04` |
| `0x00a5cb23` | `0x04` |
| `0x00a5cd9a` | `0x04` |
| `0x00a5d1b8` | `0x04` |

No direct imported `VirtualAlloc` call requests an executable page protection.

## Adjudication

`direct_standard_win32_runtime_patching_subset_complete=true`.

For this bounded class:

- direct imported code-page protection/write API found = false;
- direct `VirtualAlloc` executable allocation found = false;
- `VirtualAlloc` static-reference surface complete = true.

Global runtime-generated/copied pointer gates remain fail-closed. `GetProcAddress` is imported, so dynamically resolved APIs, externally supplied names/addresses, opaque helper patching, JIT-style code generation, runtime-populated function-pointer stores and copied/generated code pointers remain open.

No change is made to `manager+0x374 -> HDVehicle+0x4330`, `0x004b86cf`, P1.3, or provider count (7).
