# Process 1B — HDVehicle+0x4330 static-vtable indirect recovery

This contract closes the bounded indirect-target class backed by the pinned retail vtable candidate inventory.

Inputs:

- `SHIFT.P1B.HDVehicle4330ExactCarrierVtableSurface/1`
- `SHIFT.P1B.HDVehicle4330IncomingEntryFrontier/1`

Observed surface:

- canonical P1B carriers: 15;
- static vtable candidates: 2,533;
- static vtable slots: 22,416;
- exact carrier targets in those slots: 0;
- unresolved navigation-index indirect edges remain 19,500.

Adjudication:

`static_vtable_indirect_target_subset_complete=true` and `static_vtable_can_target_exact_p1b_carrier=false`.

This does **not** promote the global incoming-indirect gate. Runtime-written vtables, callback tables, generated/copied pointers and opaque memory targets remain open. The next recovery classes are callback-backed targets and persistent function-pointer storage.
