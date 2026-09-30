# Phase 602 — native physics participant structural boundary

Phase 599 makes the recovered CameraManager snapshot/double-buffer state live in
`SHIFT.NativeRuntimeState/1`.

Phase 602 advances the next native integration gate: the vehicle-physics
participant boundary.

The project already has source-backed contracts for four distinct facts:

- `SHIFT.VehiclePhysicsParticipantGate/1` — IGPhaseVehicle selection/wait/load
  control flow;
- `SHIFT.PhysicsParticipantRegistryUpdate/1` — the
  `DAT_00c109e0` participant slot registry;
- `SHIFT.VehiclePhysicsSelectorContext/1` — the separate
  `DAT_00bbc600` selector context;
- `SHIFT.VehiclePhysicsParticipantProcessReselect/1` — the selected
  pointer/ordinal process and writeback slots.

Phase 602 joins only these proven structural facts and exposes them to the
offline native state.

## Contract

New module:

`src/physics/native_physics_participant_boundary.py`

emits:

`SHIFT.NativePhysicsParticipantBoundary/1`.

The contract is ready only when the existing source-backed reports still agree
on:

- PhysicsParticipantManager global: `DAT_00c109e0`;
- registry slot array: `manager+0x140`;
- registry slot count: `manager+0x148`;
- registry slot stride: `0x1fa0`;
- participant descriptor type gate: `descriptor+0x1c == 3`;
- selector global: `DAT_00bbc600`;
- manager and selector are explicitly **not** claimed to be the same object;
- IGPhaseVehicle selected pointer slot: `+0x450`;
- selected ordinal slot: `+0x454`;
- phase state slot: `+0x45c`.

Any drift in those relationships blocks the boundary.

## Runtime instance policy

This phase does **not** create or select a retail runtime participant.

The generated contract therefore fixes:

```text
participant_instance_ready = false
participant_index          = -1
participant_mode           = -1
```

and records:

- selected runtime instance proven = false;
- selected provider proven = false;
- numeric physics equivalence proven = false.

This is intentional. Static/control-flow evidence cannot be promoted into a
concrete retail participant pointer or provider instance.

## native_runtime

The runtime adds the optional argument:

```text
--participant-boundary FILE
```

The loader requires:

- `SHIFT.NativePhysicsParticipantBoundary/1`;
- `ready = true`;
- exact `DAT_00c109e0` manager identity;
- exact `DAT_00bbc600` selector identity;
- explicit selector/manager separation;
- `registry_slot_stride = 8096`;
- `participant_descriptor_type = 3`;
- unresolved participant instance fields
  `false / -1 / -1`.

On success the native state records only the structural ABI:

- participant contract ready;
- registry contract ready;
- selector context separate;
- registry slot stride;
- participant descriptor type.

The runtime then explicitly reasserts:

- `participant_ready = false`;
- `participant_index = -1`;
- `participant_mode = -1`.

## Telemetry

`SHIFT.NativeRuntimeFrameLoop/1` now exposes:

- `physics_participant_contract_ready`;
- `physics_participant_registry_ready`;
- `physics_selector_context_separate`;
- `physics_registry_slot_stride`;
- `physics_participant_descriptor_type`;
- the existing unresolved participant ready/index/mode fields.

This lets CI prove that the structural contract reached native state without
overclaiming an observed participant instance.

## Linux CI

The neutral scene-set smoke generates the Phase 602 contract from the source
contracts and launches:

```bash
shift_runtime \
  --scene-set ... \
  --physics-manifest ... \
  --participant-boundary native_physics_participant_boundary.json \
  ...
```

The run must report:

```text
physics_participant_contract_ready     = true
physics_participant_registry_ready     = true
physics_selector_context_separate      = true
physics_registry_slot_stride           = 8096
physics_participant_descriptor_type    = 3
physics_participant_ready              = false
physics_participant_index              = -1
physics_participant_mode               = -1
```

## Boundary after Phase 602

The source-backed participant registry/selector ABI is now admitted to
`SHIFT.NativeRuntimeState/1`.

Still runtime-capture gated:

- the concrete selected participant instance;
- selected participant index/mode;
- provider identity;
- provider acceptance state;
- provider numeric parity;
- actual force/integration execution.

The next physics-native step may connect further structural lifecycle state, or
the 40-scalar solver workspace to a native numerical backend, but neither may
invent a retail participant/provider instance.
