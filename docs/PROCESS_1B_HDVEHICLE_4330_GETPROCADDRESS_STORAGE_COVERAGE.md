# Process 1B: bounded GetProcAddress result-storage coverage

This contract composes the corrected CFG-aware imported resolver surface with every bounded result-lineage closure currently available.

## Inputs

- `SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/2`
- `SHIFT.P1B.HDVehicle4330GetProcAddressWrapperOutputPersistence/1`
- `SHIFT.P1B.HDVehicle4330GetProcAddressDirectResultLineage/1`
- `SHIFT.P1B.HDVehicle4330GetProcAddressRegisterLoadedResultLineage/1`

## Composed surface

- physical imported `GetProcAddress` callsites: **101**;
- direct IAT calls: **12**;
- IAT-load roots: **7**;
- CFG-aware register-loaded calls: **89**;
- direct generic-wrapper callers: **12**;
- wrapper persistent non-stack stores: **0**;
- direct-IAT persistent global lineages: **3**, exact P1B carrier identities: **0**;
- register-loaded families: **7** across six external DLLs, exact P1B carrier identities: **0**.

Every statically reachable imported-`GetProcAddress` result lineage in this bounded model is classified. None can seed one of the 15 internal `HDVehicle+0x4330` carrier addresses.

## Gate discipline

Promoted only:

- `bounded_static_getprocaddress_result_storage_complete=true`;
- `bounded_static_getprocaddress_storage_can_seed_internal_carrier=false`.

The aggregate does **not** close runtime-created resolver aliases, indirect/runtime-generated wrapper entry, external function pointers, unrelated runtime-populated tables, generic function-pointer stores/copies, runtime patching, global carrier indirect entry, the `manager+0x374 -> HDVehicle+0x4330` join, `0x004b86cf`, or aggregate P1.3. Provider count remains 7.
