# Process 1B — HDVehicle+0x4330 carrier self-propagation closure

`SHIFT.P1B.HDVehicle4330CarrierSelfPropagationClosure/1` composes two already-merged bounded surfaces for the canonical 15 P1B `HDVehicle+0x4330` carrier functions.

## Closed subset

- exact canonical carriers: 15;
- Ghidra-indexed `CALLIND` edges whose caller is one of those carriers: 0;
- source-visible carrier address-taking uses: 0;
- source-visible non-call carrier-as-value uses: 0;
- direct known-carrier value copy/store origins: 0.

Within this bounded model, an already-proven carrier does not self-propagate through an outgoing indirect dispatch or by escaping its own exact code address as a directly copyable function-pointer value.

## What remains open

This does **not** close incoming indirect entry into a carrier. It also does not close callbacks registered outside the carrier set, runtime-created or table-derived code pointers, cross-block reconstruction, runtime patching, or opaque external pointer sources.

The indirect-call side is navigation evidence from the hash-pinned Ghidra SQLite index. Semantic identity of the 15 carriers remains owned by the merged retail machine contracts.

Global `runtime_generated_or_copied_function_pointers`, `generic_function_pointer_stores_copies`, `indirect_entry_into_carriers`, `manager+0x374 -> HDVehicle+0x4330`, `0x004b86cf`, and aggregate P1.3 gates remain fail-closed. Provider count remains 7.
