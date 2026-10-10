# Process 1B: selected non-thread HDVehicle+0x4330 callback closure

## Scope

This contract composes the 11 direct non-thread callback-capable callsites originally pinned by `SHIFT.P1B.HDVehicle4330NonThreadCallbackFrontier/1`.

It does **not** claim global runtime callback closure. Generic function-pointer stores/copies, other callback-registration APIs, computed/encoded code pointers and unresolved indirect dispatch remain separate work.

## Result

All 11/11 pinned callsites now have callback-argument provenance:

- `RegisterClassExW`: 3 callsites, all `lpfnWndProc = FUN_00634870`.
- `ReadFileEx`: 2 callsites, both `lpCompletionRoutine_006553e0`.
- `WriteFileEx`: 2 callsites, both `lpCompletionRoutine_00655410`.
- `SetWaitableTimer`: 2 machine callsites, both completion routines `NULL`.
- `WSARecv`: completion routine `NULL`.
- `WSARecvFrom @ 0x005fdd09`: x86 ABI reconstruction proves argument 9 `lpCompletionRoutine = NULL`; provenance is `0x005fdc98 xor ebp,ebp` followed by `0x005fdce1 push ebp` with no intervening EBP write.

The three distinct non-null callbacks (`0x00634870`, `0x006553e0`, `0x00655410`) are not members of the canonical P1B exact `HDVehicle+0x4330` carrier set.

Therefore this selected frontier contains:

- 11 resolved callsites;
- 7 non-null callback callsites;
- 4 null callback callsites;
- 0 unresolved callsites;
- 0 exact `HDVehicle+0x4330` carrier callbacks.

## Gate discipline

The selected callback frontier is complete, but the global gates remain fail-closed:

- `runtime_callback_registration_ruled_out = false`
- `indirect_entry_into_carriers_ruled_out = false`
- `global_runtime_derived_4330_alias_surface_complete = false`
- `manager_374_join_to_hdvehicle_4330_complete = false`
- `last_literal_0x004b86cf_rejected = false`
- `p1_3_control_producer_complete = false`
- external provider count = 7

## Inputs

The closure composes:

- `SHIFT.P1B.HDVehicle4330NonThreadCallbackTranche1/1`;
- `SHIFT.P1B.HDVehicle4330NonThreadCallbackTranche2/1`;
- `SHIFT.Process1TimerWinsockApcSurface/1`.

The final WSARecvFrom result is machine-authoritative and no longer depends on the malformed decompiler call signature.

## Next step

Continue generic runtime function-pointer stores/copies and remaining indirect-entry mechanisms. Only after those surfaces are bounded should P1B attempt the final `manager+0x374 -> HDVehicle+0x4330` identity join and `0x004b86cf` adjudication.
