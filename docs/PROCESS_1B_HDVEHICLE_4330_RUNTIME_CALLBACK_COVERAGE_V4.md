# Process 1B — HDVehicle+0x4330 runtime callback coverage `/4`

`SHIFT.P1B.HDVehicle4330RuntimeCallbackCoverage/4` supersedes `/3` as the current bounded callback baseline.

## Delta from `/3`

The new dedicated `_bsearch` machine closure contributes:

- 2 physical `_bsearch` callsites;
- 2 fixed comparator entrypoints: `0x0053c280`, `0x00a5df20`;
- 0 exact hits on the 15 canonical P1B `HDVehicle+0x4330` carriers.

The first comparator is machine-proven despite the Ghidra `unaff_retaddr` rendering: `0x00429e86` explicitly pre-pushes `0x0053c280` before tail-jumping into the shared `_bsearch` body. The second site directly pushes `0x00a5df20`.

## Aggregate

```text
closed bounded callback surfaces       8
physical callback-capable callsites   51
unique possible callback entrypoints  36
exact P1B carrier entrypoint hits       0
```

The eight surfaces are:

1. `CreateThread` / `__beginthreadex`;
2. selected Win32/Winsock non-thread callbacks;
3. `FUN_0061cdf0` Massive callback wrapper;
4. CRT `_qsort` comparators;
5. WinMM waveOut/waveIn/timeSetEvent callbacks;
6. `SetUnhandledExceptionFilter`;
7. `CreateFiber`;
8. CRT `_bsearch` comparators.

## Gate discipline

This aggregate remains bounded. It does not promote any global indirect-entry gate.

Still fail-closed:

```text
runtime_callback_registration_ruled_out = false
remaining_callback_api_families_ruled_out = false
generic_function_pointer_stores_copies_ruled_out = false
computed_or_encoded_code_pointers_ruled_out = false
indirect_entry_into_carriers_ruled_out = false
global_runtime_derived_4330_alias_surface_complete = false
manager_374_join_to_hdvehicle_4330_complete = false
last_literal_0x004b86cf_rejected = false
p1_3_control_producer_complete = false
provider count = 7
```

## Next step

Use `/4` as the no-duplication callback baseline and continue the remaining callback/API and runtime-generated/copied/encoded function-pointer surfaces.
