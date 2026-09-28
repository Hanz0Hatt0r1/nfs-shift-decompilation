# Phase 508 — vehicle physics selector context

## Goal

Resolve the object identity of the IGPhaseVehicle participant selector itself
and make the separation from the PhysicsParticipantManager global explicit.

Contract:

SHIFT.VehiclePhysicsSelectorContext/1

## Source-backed identity

thunk_FUN_00453990 is a thin wrapper over FUN_00402435.
FUN_00402435 lazily constructs and returns:

&DAT_00bbc600

The same global is initialized by FUN_00410490 and cleaned up by FUN_00411430.

Inside FUN_00410ef0, the selector storage is the member at:

context+0x9fc

The descriptor table is observed at:

- count: context+0x1c
- base: context+0xb8
- stride: 0x90
- name: descriptor+0x10

FUN_004102d0 initializes the selector storage through
FUN_004f0050(context+0x9fc, ...).

## Matching path

FUN_00410ef0:

1. ensures selector storage is initialized;
2. clears/rebuilds selector state when required;
3. initializes descriptor ordinal shadows at context+0x144;
4. inserts each source descriptor into selector storage using FUN_00800dd0;
5. links unresolved descriptors by case-insensitive name via __stricmp;
6. treats empty/null names as a match;
7. repeats until all descriptors are linked or a fallback ordinal remains;
8. enumerates selector storage through FUN_0052cce0;
9. selects the first candidate whose byte at candidate+0x74 is zero;
10. returns the selector-storage ordinal, or -1 after FUN_00688010 when no
    candidate satisfies that observed condition.

This closes an important distinction: the selector storage is not shown as
DAT_00c109e0.

## Separation from Phases 506–507

Phases 506–507 established DAT_00c109e0 as the global used by
PhysicsParticipantManager event ingestion and participant slot
allocation/registration/update.

Phase 508 therefore records:

selector global = DAT_00bbc600
participant-manager global = DAT_00c109e0

and explicitly sets the identity join to false until runtime or stronger
cross-reference evidence proves otherwise.

## Scope boundary

No C++ class name is assigned to DAT_00bbc600. The generic enumerator
FUN_0052cce0 is kept generic. No runtime participant identity or provider
identity is inferred.

Provider numerical equivalence still requires an authentic runtime frame.
