# Phase 602 — native vehicle participant topology boundary

Phase 601 proves deterministic throttle/brake/steer intent reaches the native
fixed-step physics boundary. The next integration problem is participant
identity.

The retail source evidence contains two different participant-related domains:

- `DAT_00c109e0`: the PhysicsParticipantManager slot registry/update object
  proven by Phase 507;
- `DAT_00bbc600`: the IGPhaseVehicle selector context proven by Phase 508.

Phase 509 proves that the selector ordinal is stored at
`IGPhaseVehicle+0x454`, while Phase 507 proves that the manager registry index
comes from `PhysicsParticipant+0x3c`.

No source or runtime evidence currently proves that those integers identify
the same object or even use the same numbering domain.

## Bridge contract

Phase 602 adds:

`SHIFT.NativeVehicleParticipantBridge/1`

implemented by:

`src/physics/native_vehicle_participant_bridge.py`.

The bridge validates the existing source-backed contracts:

- `SHIFT.VehiclePhysicsParticipantGate/1`;
- `SHIFT.PhysicsParticipantRegistryUpdate/1`;
- `SHIFT.VehiclePhysicsSelectorContext/1`;
- `SHIFT.VehiclePhysicsParticipantProcessReselect/1`.

It then freezes the native-visible topology:

- participant-manager global: `DAT_00c109e0`;
- selector global: `DAT_00bbc600`;
- manager slot array: `+0x140`;
- manager slot count: `+0x148`;
- manager slot stride: `0x1fa0`;
- registry index source: `PhysicsParticipant+0x3c`;
- selected pointer slot: `IGPhaseVehicle+0x450`;
- selector ordinal slot: `IGPhaseVehicle+0x454`;
- process-state slot: `IGPhaseVehicle+0x45c`;
- candidate readiness byte: `candidate+0x74`.

The bridge explicitly emits:

- `native_participant_topology_ready = true`;
- `native_participant_ready = false`;
- `native_registry_index = -1`;
- `native_selector_ordinal = -1`;
- `registry_selector_identity_join_proven = false`.

## Native runtime

`native_runtime/shift_runtime` adds:

```text
--participant-bridge FILE
```

The runtime revalidates the exact globals and offsets before applying the
bridge.

`PhysicsTickBoundary` now carries separate fields for:

- participant registry index;
- selector ordinal;
- IGPhaseVehicle process state;
- topology readiness;
- manager/selector separation;
- identity-join proof.

The old `participant_index` / `participant_mode` fields remain compatibility
aliases but stay `-1` until a future observed identity join is strong enough
to set `participant_ready=true`.

## Fixed-step observability

Each fixed step counts one of two participant states after topology admission:

- `participant_ready_steps`;
- `participant_unresolved_steps`.

The Phase 602 CI run loads the topology bridge together with the Phase 600
camera bridge and Phase 601 five-step input script.

Expected result:

- topology ready: true;
- manager/selector distinct: true;
- identity join proven: false;
- participant ready: false;
- registry index: -1;
- selector ordinal: -1;
- topology steps: 5;
- ready steps: 0;
- unresolved steps: 5.

This proves the participant boundary is executed by the same fixed-step
scheduler that receives vehicle input without fabricating a participant.

## CLI

```bash
python shift_importer.py native-vehicle-participant-bridge \
  out/native-participant.json
```

## Boundary after Phase 602

Phase 602 does **not** select a provider, dereference a retail participant
pointer or apply forces.

To promote `participant_ready`, a later runtime observation must independently
join the manager registry identity to the selected IGPhaseVehicle participant
while preserving the selector ordinal as a separate observed field.

Specialized-provider numerical parity remains gated on an authentic runtime
frame.
