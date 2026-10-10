# Process 1B — HDVehicle+0x4330 incoming-entry frontier

This contract composes the already-complete direct incoming call inventory and its machine-level external receiver adjudication with the capability limit of the shared Ghidra SQLite indirect-call index.

## Result

- canonical P1B carriers: 15
- incoming direct callsites: 25
  - internal carrier-to-carrier: 14
  - external: 11 across 7 callers
- unresolved external direct callers after machine adjudication: 0
- external direct pre-existing `HDVehicle+0x4330` aliases: 0
- shared navigation-index indirect edges: 19,500
- resolved indirect targets in that index: 0
- unresolved indirect targets: 19,500

The direct incoming surface is therefore no longer part of the open P1B incoming-entry blocker. The remaining incoming-entry uncertainty is specifically target recovery for unresolved indirect calls.

## Important limit

Zero resolved indirect carrier hits is **not** an absence proof because the current SQLite index resolves none of its indirect edges. Machine/vtable/callback/function-pointer storage dataflow is still required.

The P1A incoming-indirect-index contract is consumed only for the shared SQLite index capability counts; its 16-carrier semantics are not imported into Process 1B.

Global indirect-entry, runtime-generated/copied pointer, manager identity, final literal, P1.3, and provider gates remain fail-closed. Provider count remains 7.
