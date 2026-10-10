# Process 1B — exact Participants Manager root alias closure

This contract composes the already-merged whole-image persistence evidence for the exact value returned by `FUN_00489ad0()` with the current bounded `manager+0x374` writer coverage.

## Closed exact-root alias classes

The authoritative persistence scan covers **394** direct calls to `FUN_00489ad0` in PC retail 1.02.

For the exact returned manager root:

- stack persistence: **9** saves, all bounded;
- object/global persistence: **0** stores;
- immediate stack-argument forwarding: **0** `push eax` cases after the getter;
- immediate local stores: **2**, both already bounded read/receiver paths;
- delayed stack aliases are already consumed by `SHIFT.HDVehicle64e8Manager374GetterPersistenceClosure/1`.

Therefore exact getter-derived storage/stack argument paths cannot create a new writer that places fixed `HDVehicle+0x4330` into `manager+0x374`.

## Gate update

This composition promotes only the exact-getter-root alias classes:

- `escaped_storage_paths_complete=true`;
- `stack_argument_alias_paths_complete=true`;
- `exact_getter_root_alias_surface_complete=true`.

It does **not** close arithmetic/non-immediate reconstruction of the Participants Manager singleton root, helper-mediated writes reached through such reconstructed roots, or non-vtable indirect setters. Those remain the next Process 1B frontier.

The aggregate identity join, final `0x004b86cf` / slot2 adjudication, P1.3 completion, and provider removal all remain fail-closed. Provider count remains **7**.
