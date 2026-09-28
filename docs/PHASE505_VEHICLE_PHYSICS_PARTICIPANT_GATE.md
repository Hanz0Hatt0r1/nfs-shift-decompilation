# Phase 505 — vehicle physics participant creation gate

## Goal

Phase 505 closes the next source/control-flow boundary before runtime provider
capture:

`IGPhaseVehicle → participant selection → wait/success gate → vehicle BFF load`

Contract:

`SHIFT.VehiclePhysicsParticipantGate/1`

## Source-backed evidence

The retail decompilation shows the phase vehicle update path calling
`FUN_00410ef0` through a context returned by `thunk_FUN_00453990`.

The selector:

- works from a descriptor count at `selection_context+0x1c`;
- walks descriptors from `selection_context+0xb8` with `0x90` stride;
- uses the descriptor name at `+0x10` for case-insensitive linking;
- writes the descriptor ordinal at descriptor `+0x0`;
- iterates candidate entries and accepts a candidate only when byte
  `candidate+0x74 == 0`;
- writes the candidate pointer through `IGPhaseVehicle+0x450`;
- returns the candidate ordinal, stored by the caller at `IGPhaseVehicle+0x454`.

When the selector returns `-1`, the caller logs
`IGPhaseVehicle: Waiting for Physics Participant Create` and returns `4`
before starting the base vehicle load.

On success the same caller formats:

`Pakfiles/Vehicles/%s.bff`

and continues the vehicle load path. The cockpit branch remains separate and
uses:

`Pakfiles/Vehicles/%s_cockpit.bff`

## Why this matters

This identifies a concrete control-flow gate between participant availability and
vehicle resource loading. It is stronger than a generic statement that a
"physics participant" exists, while still avoiding an invented engine/PhysX
class identity.

The gate is now represented as machine-readable JSON and can be consumed by the
BFF-to-pre-PhysX handoff tooling.

## Scope boundary

This phase does not identify what class owns `candidate+0x74`, does not select
the retail provider, and does not claim runtime participant identity. Those
remain capture-backed questions.
