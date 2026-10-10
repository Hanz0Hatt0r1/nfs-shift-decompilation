# Process 1B — HDVehicle+0x4330 `_qsort` callback surface

## Scope

This contract closes the CRT `_qsort` comparator callback surface for the canonical Process 1B exact `HDVehicle+0x4330` carrier set.

Inputs are the pinned PC retail 1.02 Ghidra SQLite index and matching `SHIFT.exe.c` export. They are used as navigation/cross-check evidence; no selected-object identity is inferred from decompiler types.

## Result

The SQLite call inventory contains exactly **16 direct `_qsort` callsites**.

The callback arguments resolve to **17 possible comparator entrypoints** because the shared `_qsort` call at `0x004baeff` can receive one of two local comparator assignments:

- `FUN_004ba980`
- `FUN_004bac50`

The remaining callsites have fixed comparator functions or labels. The stack-materialized site at `0x009aeec0` is pinned to `LAB_009aede8` before the call.

None of the 17 possible comparator entrypoints is a member of the canonical 15-function P1B exact `HDVehicle+0x4330` carrier set.

Therefore:

- `qsort_callback_surface_complete = true`
- `exact_4330_carrier_reachable_via_qsort = false`

## Limits

This does **not** close all runtime callbacks or indirect entry. It covers only the 16 direct CRT `_qsort` registrations in the pinned retail SQLite/source pair.

Application-owned wrappers, other CRT callback mechanisms, generic function-pointer stores/copies, reconstructed pointers and computed indirect entry remain open. Accordingly:

- `runtime_callback_registration_ruled_out = false`
- `indirect_entry_into_carriers_ruled_out = false`
- `global_runtime_derived_4330_alias_surface_complete = false`
- `manager_374_join_to_hdvehicle_4330_complete = false`
- `last_literal_0x004b86cf_rejected = false`
- `p1_3_control_producer_complete = false`
- external provider count remains **7**.

## Next step

Continue finite CRT/application callback mechanisms and generic runtime function-pointer stores/copies before promoting any global callback/indirect-entry gate or attempting the final manager identity join.
