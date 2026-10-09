# Process 1D — Controller #1 direct `GetProcAddress` reachability

## Result

The current `shift_ghidra.sqlite` evidence database was queried from the exact Controller #1 worker `FUN_00662880`.

The direct internal callgraph reaches **497** functions. The whole database contains **100** direct `GetProcAddress` callsites across **18** caller functions. Only **6** of those caller functions are reachable from the Controller #1 worker through the direct callgraph.

Their locally owned defined strings resolve to CRT/UI/runtime APIs such as `CorExitProcess`, `EncodePointer`, `DecodePointer`, `InitializeCriticalSectionAndSpinCount`, `GetUserObjectInformationA`, `GetLastActivePopup`, `GetActiveWindow`, and `MessageBoxA`. None of the six reachable resolver functions owns a local literal for `QueueUserAPC`, `NtQueueApcThread`, `NtQueueApcThreadEx`, `ZwQueueApcThread`, `RtlQueueApcWow64Thread`, or `SetWaitableTimerEx`.

This rejects the **reachable direct `GetProcAddress` + locally defined APC literal-name** sub-surface.

## Boundary

This is not a universal dynamic-resolution closure. A resolver name may still be forwarded from a caller, constructed at runtime, decrypted, hashed, or obtained through manual export walking. Indirect calls and native/syscall injection are also outside this contract.

Therefore:

```text
reachable direct resolver local APC literal = rejected
nonlocal/generated/hashed resolver names     = open
manual export walking                        = open
native/syscall APC injection                 = open
Controller #1 timing exhaustive              = false
P1.3D complete                               = false
provider count                               = 7
```

## Reproduction

Run:

```text
python3 tools/ghidra/analyze_p1d_controller1_getproc_reachability.py \
  out/shift_ghidra.sqlite \
  --output out/p1d_controller1_getproc_reachability.json
```

The checked-in evidence pins the current Drive-backed PC retail 1.02 database counts and the six reachable resolver functions so drift is visible in CI.
