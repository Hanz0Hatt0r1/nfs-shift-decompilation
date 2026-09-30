# Phase 605 — native participant identity-domain separation

Phase 602 admits the source-backed vehicle participant structure into
`SHIFT.NativeRuntimeState/1` without fabricating a retail participant.

Phase 605 tightens that boundary around a distinction already present in the
retail source evidence.

Two integer identities are known, but they are not proven equivalent:

- PhysicsParticipantManager registry index: source field
  `PhysicsParticipant+0x3c`, consumed by `FUN_00713f40/FUN_00713ec0`;
- IGPhaseVehicle selector ordinal: returned by `FUN_00410ef0` and stored at
  `IGPhaseVehicle+0x454`.

The selector object is `DAT_00bbc600`; the participant manager is
`DAT_00c109e0`. Phases 507–509 explicitly do not prove an identity join
between those domains.

## Contract refinement

`SHIFT.NativePhysicsParticipantBoundary/1` now preserves:

- `registry_index_source = PhysicsParticipant+0x3c`;
- `registry_index_source_offset = 0x3c`;
- selector candidate readiness at `candidate+0x74`;
- `registry_selector_identity_join_proven = false`;
- `participant_registry_index = -1`;
- `selector_ordinal = -1`;
- `participant_process_state = -1`.

The Phase 602 compatibility fields remain:

- `participant_index = -1`;
- `participant_mode = -1`.

They are explicitly inactive aliases and may not be populated from either
static identity domain.

## Fail-closed checks

The bridge now blocks if:

- the manager index source is relabelled from `PhysicsParticipant+0x3c`;
- the selector ready gate drifts from `candidate+0x74 == 0`;
- any existing manager/selector source contract is not ready.

## Native state

`PhysicsTickBoundary` carries separate capture-gated fields:

- `participant_registry_index`;
- `selector_ordinal`;
- `participant_process_state`;
- `participant_identity_join_proven`.

Structural admission sets the identity join to false and all three values to
-1.

Each fixed step with an admitted structural participant contract increments
`participant_topology_steps`. It also increments exactly one of:

- `participant_ready_steps`;
- `participant_unresolved_steps`.

With Phase 605 static evidence only, every such step is unresolved.

## Runtime telemetry

`SHIFT.NativeRuntimeFrameLoop/1` adds:

- `physics_participant_identity_join_proven`;
- `physics_participant_registry_index`;
- `physics_selector_ordinal`;
- `physics_participant_process_state`;
- `physics_participant_topology_steps`;
- `physics_participant_ready_steps`;
- `physics_participant_unresolved_steps`.

The old `physics_participant_index/mode` fields remain -1 for compatibility.

## CI

The three-frame neutral scene smoke requires:

- topology steps = 3;
- ready steps = 0;
- unresolved steps = 3.

The deterministic five-step input smoke requires:

- topology steps = 5;
- ready steps = 0;
- unresolved steps = 5.

Both require registry index and selector ordinal to remain independently -1.

## Boundary after Phase 605

A future runtime-observation contract may promote a concrete participant only
if it independently observes the manager-registry identity and the selected
IGPhaseVehicle participant while retaining the selector ordinal as a separate
field.

Phase 605 does not assign a provider, force law, PhysX class or numerical
solver behavior.
