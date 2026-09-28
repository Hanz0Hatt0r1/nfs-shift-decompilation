# Phase 507 — Physics participant registry/update bridge

## Goal

Extend the static participant path from Phase 506 into the concrete participant
slot allocation and data refresh functions called by PhysicsParticipant.cpp.

Contract:

SHIFT.PhysicsParticipantRegistryUpdate/1

## Source-backed structure

The DAT_00c109e0 manager owns a participant slot array through:

- +0x140: constructed entry array;
- +0x148: slot count;
- entry stride 0x1fa0.

FUN_007146c0(manager, count) allocates and constructs the count * 0x1fa0
slot array and stores the resulting pointer/count at those fields. FUN_00714840
destructs and frees the slot array.

### Registration

FUN_00713f40(manager, index, descriptor, flag) resolves:

manager+0x140 + index * 0x1fa0

and writes:

- descriptor+0x10 = 1;
- descriptor+0x14 = index.

When the flag is zero, several descriptor fields are defaulted from the
indexed participant slot. With the flag non-zero, the existing descriptor
values are preserved except where an observed sentinel comparison requests a
default.

### Update

FUN_00713ec0(manager, index, descriptor) resolves the same indexed slot,
feeds descriptor+0x18 into FUN_00787a70(slot+0x340, ...), copies several
descriptor fields into fixed slot offsets, invokes FUN_007448c0(slot), then
stores descriptor+0x3c at slot +0x26e0.

### Direct PhysicsParticipant callsite

Inside the source-backed PhysicsParticipant.cpp path FUN_0074ddc3, after the
participant descriptor type test:

descriptor+0x1c == 3

the decompilation calls:

FUN_00713f40(&DAT_00c109e0, participant_index, descriptor, 1)

followed by:

FUN_00713ec0(&DAT_00c109e0, participant_index, descriptor)

The participant index is read from the participant structure at +0x3c.

This is a direct code-level bridge between the participant implementation and the
manager registry/update API.

## Relation to Phase 505/506

Phase 505 established the separate IGPhaseVehicle → FUN_00410ef0 selector gate.
Phase 506 established the opcode 0x20 → FUN_00714560(DAT_00c109e0) manager-event
path.

Phase 507 now proves that DAT_00c109e0 owns indexed participant slots that
are explicitly updated by PhysicsParticipant.cpp.

It still does not prove that thunk_FUN_00453990() returns DAT_00c109e0 or
that the selector's local registry is this manager's slot array. That identity
join remains capture/cross-reference gated.

## Tooling

python tools/build_physics_participant_registry_update.py -o physics_participant_registry_update.json

## Evidence boundary

No PhysX SDK class or engine object type is assigned. Field semantics are kept at
the level of observed writes and control-flow. Runtime participant identity and
numeric physics equivalence remain capture-dependent.
