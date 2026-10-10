# Process 1B — HDVehicle+0x4330 indirect-entry coverage v6

`SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/6` supersedes `/5` and adds the bounded exact-carrier self-propagation closure.

## New coverage class

For the canonical 15 P1B carrier functions:

- outgoing Ghidra-indexed `CALLIND` edges: 0;
- direct exact-carrier value copy/store origins: 0.

Together with the nine bounded classes already composed in `/5`, the aggregate now contains 10 coverage classes and still has zero exact-carrier hits in the bounded model.

## Remaining frontier

This does not close incoming indirect entry. Unrelated runtime-populated function-pointer tables, cross-block/table-derived reconstruction, runtime-created or opaque external pointer sources, and runtime patching remain open.

Global `runtime_generated_or_copied_function_pointers`, `generic_function_pointer_stores_copies`, `indirect_entry_into_carriers`, `manager+0x374 -> HDVehicle+0x4330`, `0x004b86cf`, and aggregate P1.3 gates remain fail-closed. Provider count remains 7.
