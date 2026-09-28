# Phase 509 — vehicle physics participant process/reselection loop

## Goal

Close the first concrete consumer of the participant pointer/ordinal produced by
the Phase 505 selector gate.

Contract:

SHIFT.VehiclePhysicsParticipantProcessReselect/1

## Source-backed loop

FUN_004d5f30 is the relevant IGPhaseVehicle process/update path.

Before making the next selection attempt, it reads the current participant pointer
from:

IGPhaseVehicle+0x450

and calls:

FUN_00468ed0(current_pointer+0x8c, current_pointer)

The process path then calls the Phase 508 selector directly:

FUN_00410ef0(&DAT_00bbc600, &local_8)

This is an independent direct use of the selector global resolved in Phase 508.

## Load and writeback

When the selector returns a non-negative ordinal, the process path constructs:

Pakfiles/Vehicles/%s.bff

and calls the observed vehicle-BFF load routine.

The existing participant pointer/ordinal remain unchanged while this load is being
attempted. Only after the load reports success does the process path replace:

- IGPhaseVehicle+0x454 with the new ordinal;
- IGPhaseVehicle+0x450 with the new pointer.

The loop repeats, so the same two fields are both the Phase 505 output and the
Phase 509 persistent process/reselection state.

The loop terminates on either:

- selector return -1;
- failed next vehicle-BFF load.

After the loop the path calls FUN_004d5930, logs
IGPhaseVehicle: Process Done, and returns through the object's vtable.

## State-2 cockpit branch

Before the loop, IGPhaseVehicle+0x45c == 2 takes a separate cockpit-processing
branch. It uses FUN_00481d40 on the +0x374 object, calls FUN_004d5160,
moves the state to 3, runs FUN_00d7f900, calls FUN_004d5930, and logs
IGPhaseVehicle: Process Cockpit Done.

That branch is kept in the contract because it is an explicit state transition in
the same process function, but it is not conflated with the participant
reselection loop.

## Cross-phase closure

Phase 505 established:

selector result → IGPhaseVehicle+0x450/+0x454

Phase 508 established:

thunk_FUN_00453990/FUN_00402435 → DAT_00bbc600

Phase 509 now proves:

IGPhaseVehicle+0x450 → FUN_00468ed0 → FUN_00410ef0(&DAT_00bbc600) → BFF load → successful +0x450/+0x454 writeback

This is a concrete static consumer path rather than another isolated structure
description.

## Evidence boundary

No engine/PhysX class name is assigned. No physical units are inferred. No runtime
candidate identity or provider numeric equivalence is claimed.
