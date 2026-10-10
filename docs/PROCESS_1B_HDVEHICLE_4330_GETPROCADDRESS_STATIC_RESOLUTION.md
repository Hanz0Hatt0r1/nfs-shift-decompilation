# Process 1B: static GetProcAddress resolution surface

## Scope

This contract bounds statically recoverable Win32 `GetProcAddress` usage in authoritative PC retail 1.02 `SHIFT.exe` (SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`). It follows the direct Win32 runtime-patching subset and asks whether known dynamic API resolution reopens code-page protection/write paths.

## Exact IAT reference surface

`GetProcAddress` is imported at IAT slot `0x00aa62fc`.

The little-endian IAT address occurs exactly **19** times in the full retail image, and objdump classifies all 19 occurrences:

- 12 direct IAT calls;
- 7 loads of the imported function pointer into a register;
- 0 unclassified static IAT references.

The seven loaded-register lifetimes contain **86** calls through the loaded `GetProcAddress` pointer before the register is overwritten or the function returns. Together with the 12 direct IAT calls this gives **98** physical resolution callsites.

## Generic wrapper

One direct IAT call is inside generic wrapper `0x0093dd2b`, whose `GetProcAddress` call is `0x0093dd43`.

The retail direct-call surface to that wrapper contains exactly **12** callers. All 12 proc names are recovered, including six FMOD names assembled from fixed format strings and `_` / `@0` substitutions:

- `_FMODGetCodecDescription@0`
- `_FMODGetCodecDescriptionEx@0`
- `_FMODGetDSPDescription@0`
- `_FMODGetDSPDescriptionEx@0`
- `_FMODGetOutputDescription@0`
- `_FMODGetOutputDescriptionEx@0`
- `VSTPluginMain`
- `main`
- `winampDSPGetHeader2`
- `AvSetMmThreadCharacteristicsA` (three direct callers)

## Recovered proc-name surface

Combining direct IAT calls, register-loaded calls and direct callers of the generic wrapper yields:

- **109** known proc-name instances;
- **105** unique proc names;
- known Win32 patch/protection API hits = **0**.

The surface includes expected runtime/library APIs such as `IsWow64Process`, `GetActiveWindow`, `EnumDisplayDevicesA`, `alGetProcAddress`, and `alcGetProcAddress`. The OpenAL names are ordinary proc names being resolved through Win32 `GetProcAddress`; they are not evidence of Win32 code-page patching.

None of these known names is one of:

- `VirtualProtect`
- `VirtualProtectEx`
- `WriteProcessMemory`
- `FlushInstructionCache`
- `VirtualAllocEx`
- `NtProtectVirtualMemory`
- `ZwProtectVirtualMemory`

## Adjudication

The following bounded gates become true:

- `static_getprocaddress_iat_reference_surface_complete=true`;
- `register_loaded_getprocaddress_call_surface_complete=true`;
- `generic_wrapper_direct_caller_name_surface_complete=true`.

`known_getprocaddress_patch_api_resolution_found=false`.

Global dynamic/runtime gates remain fail-closed. In particular, this does **not** prove absence of:

- indirect/runtime-generated callers of wrapper `0x0093dd2b`;
- proc names constructed from runtime input;
- externally supplied module/procedure addresses;
- opaque helper resolution;
- runtime-populated function-pointer stores;
- generated/copied/encoded carrier pointers.

Accordingly `dynamic_getprocaddress_resolution_ruled_out`, `runtime_patching_or_generated_code_ruled_out`, `indirect_entry_into_carriers_ruled_out`, the manager identity join, `0x004b86cf`, and aggregate P1.3 remain false. Provider count remains 7.
