# Phase 506 — PhysicsParticipantManager event path

## Goal

Close the next static boundary around the vehicle physics participant without
assuming that two similarly named subsystems are the same runtime registry.

Contract:

`SHIFT.PhysicsParticipantManagerEvent/1`

## Source-backed path

The retail decompilation contains an internal event producer:

`FUN_0070e1c0`

It creates an event with:

- channel byte `+0x05 = 3`;
- opcode byte `+0x04 = 0x20`;
- caller-supplied payload copied after the event header.

Two physics event-loop paths, `FUN_00711210` and `FUN_007112d8`, dispatch
opcode `0x20` to:

`FUN_00714560(&DAT_00c109e0, event)`

The consumer copies 31 dwords from the event payload, imports a count from
`event+0xb0), copies nested entries from `event+0x8c`, optionally imports a
byte blob, and marks:

`DAT_00c109e0 + 0x39c = 1`

The surrounding source-path assertions explicitly reference
`PhysicsParticipantManager.cpp`.

## Join with Phase 505

Phase 505 independently established:

`IGPhaseVehicle → FUN_00410ef0 → participant pointer/index → wait/success → vehicle BFF load`

The selector uses a context returned by `thunk_FUN_00453990` and iterates a
registry whose accepted candidate satisfies `candidate+0x74 == 0`.

Phase 506 does **not** claim that `DAT_00c109e0` is that exact registry.
The current decompilation proves the manager event path and the selector path,
but not their runtime object identity or direct causal relationship.

That distinction is intentional: the remaining join should be closed by a
stronger cross-reference or runtime capture rather than by naming guesses.

## Tooling

`python tools/build_physics_participant_manager_event.py -o physics_participant_manager_event.json`

The generated JSON is machine-readable and keeps the event path separate from
the Phase 505 selector contract.

## Evidence boundary

No PhysX SDK class, engine object type, or runtime participant identity is
invented. Numeric physics equivalence remains capture-dependent.
