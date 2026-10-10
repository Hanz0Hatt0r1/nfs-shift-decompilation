# Process 1B: register-loaded GetProcAddress result lineage

This consumes the corrected CFG-aware resolver surface `SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/2` and classifies all 89 register-loaded `GetProcAddress` results by their storage/consumption lineage.

## Seven bounded families

- `0x0090abf7`, KERNEL32.DLL: 2 calls, two object-field sinks (`EncodePointer`, `DecodePointer`).
- `0x0090aeac`, KERNEL32.DLL: 4 calls, four absolute globals (`FlsAlloc/Get/Set/Free`).
- `0x0091c0b0`, USER32.DLL: 5 calls, five encoded absolute globals.
- `0x0096daa2`, wnaspi32.dll: 2 calls, two absolute globals.
- `0x00999fe7`, dsound.dll: 6 calls, four object-field destinations with fallback overwrites.
- `0x009a7e40`, openal32.dll: 67 calls, exactly 67 sequential caller-provided table slots from `+0x0` through `+0x108`.
- `0x00a62354`, gdi32.dll: 3 calls; `EnumDisplayDevicesA` is stack-local and D3DKMT exports remain register/helper-local. The complete helper `0x00a62160` consumes them but does not persist raw function pointers.

All 89 values are exports of six external DLLs. Therefore this bounded resolver-populated storage surface cannot contain any of the 15 internal `SHIFT.exe` P1B carrier addresses. Exact internal carrier identity hits: **0**.

## Gate discipline

Promoted only:

- `cfg_aware_register_loaded_result_lineage_subset_complete=true`;
- `resolver_populated_bounded_storage_surface_complete=true`;
- `resolver_populated_storage_can_hold_exact_internal_p1b_carrier=false`.

Runtime-created resolver aliases, unrelated runtime-populated tables, external/opaque function pointers, global indirect entry, manager+0x374 identity, `0x004b86cf` and aggregate P1.3 remain fail-closed. Provider count remains 7.
