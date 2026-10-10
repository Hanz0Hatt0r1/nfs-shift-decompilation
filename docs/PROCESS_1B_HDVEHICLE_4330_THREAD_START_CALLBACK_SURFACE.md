# Process 1B — HDVehicle+0x4330 thread-start callback surface

This slice bounds the explicit Win32/CRT thread-start registration subset that could provide an indirect entry into one of the already-proven exact `HDVehicle+0x4330` carrier functions.

Inputs are hash-pinned retail artifacts:

- `shift_ghidra.sqlite` SHA-256 `ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e`;
- `SHIFT.exe.c` SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`.

The Ghidra call index contains exactly seven direct `CreateThread` callsites and three direct `__beginthreadex` callsites. Their resolved start routines are:

- `0x005d5f40`;
- `0x005fdd70`;
- `0x005ff1e0`;
- `0x005ff710`;
- `0x0061cd93`;
- `0x00649b10`;
- `0x00907e4f`;
- `0x009396c0`;
- `0x00a2a370`.

None is one of the 15 exact P1B `HDVehicle+0x4330` carriers.

`FUN_0093db2b` is the only `CreateThread` wrapper in this subset whose start routine is supplied as a parameter. Its direct callgraph surface contains exactly one caller, `FUN_00939797 @ 0x0093984a`, and the pinned source passes `FUN_009396c0` in that parameter. The two game-side `__beginthreadex` wrappers use fixed `FUN_00649b10` and `FUN_00a2a370`; CRT `__beginthreadex` itself starts through fixed `lpStartAddress_00907e4f`.

Therefore the explicit thread-start registration subset is closed negative for exact `HDVehicle+0x4330` carrier entry.

This is not a global callback-registration proof. Window procedures, timers, hooks, APCs, wait callbacks, multimedia/plugin callbacks, arbitrary function-pointer stores and computed/copied/encoded pointer paths remain open. Consequently `runtime_callback_registration_ruled_out`, `indirect_entry_into_carriers_ruled_out`, the manager `+0x374 -> HDVehicle+0x4330` identity join, final `0x004b86cf`, P1.3 completion and provider removal remain fail-closed.
