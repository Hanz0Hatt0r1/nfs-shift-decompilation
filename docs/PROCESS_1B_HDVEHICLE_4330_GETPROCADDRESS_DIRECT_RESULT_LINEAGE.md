# Process 1B: direct GetProcAddress result lineage

## Scope

This contract classifies result lineage for all 12 direct machine calls to the imported `GetProcAddress` IAT slot `0x00aa62fc` in retail PC 1.02 `SHIFT.exe`.

It builds on the static resolver surface and the separate direct generic-wrapper output-persistence closure.

## Result

All 12 direct IAT callsites are classified. Three persistent global lineages exist:

1. `InitializeCriticalSectionAndSpinCount` is resolved at `0x00918a26`, passed through the bounded EncodePointer helper, stored encoded in `0x00c328c8`, later decoded through DecodePointer and invoked. The exact global has three machine references.
2. `WMCreateSyncReader` from `wmvcore.dll` is resolved at `0x009506b9`, stored in `0x00c593b0`, and called at `0x0095073b`. The exact global has three machine references.
3. `ReadDirectoryChangesW` from `kernel32.dll` is resolved at `0x00a9ab1a` and stored in `0x00cce308`; its exact absolute global address has two machine references (store and zeroing) and no exact direct call.

Persistent exact-carrier identity hits across these three lineages: **0**.

The other direct-IAT result paths are transient/local, bounded return-helper paths, or the generic wrapper already closed by `SHIFT.P1B.HDVehicle4330GetProcAddressWrapperOutputPersistence/1`. `FUN_007d6550` (`GetEventHandler`) has exactly two direct callers; one only checks the returned pointer and one immediately calls it.

## Gates

Promoted only for this bounded class:

- `direct_getprocaddress_result_lineage_subset_complete=true`
- `direct_getprocaddress_persistent_global_lineage_complete=true`
- `direct_getprocaddress_persistent_carrier_identity_found=false`

The 86 register-loaded `GetProcAddress` calls remain independent and open. Therefore global runtime-generated/copied pointer, dynamic resolver, indirect-entry, manager join, final literal, and P1.3 gates remain fail-closed. External provider count remains 7.

## Next step

Classify result lineages from the 86 register-loaded `GetProcAddress` calls and compose bounded resolver-populated function-pointer storage coverage.
