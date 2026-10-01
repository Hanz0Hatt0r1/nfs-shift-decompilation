# Phase 607 — native participant runtime identity evidence

Phase 605 separates two retail identity domains that static evidence does not
prove equivalent:

- PhysicsParticipantManager registry index from
  `PhysicsParticipant+0x3c`;
- IGPhaseVehicle selector ordinal stored at
  `IGPhaseVehicle+0x454`.

Phase 607 adds the fail-closed runtime observation join required before a
concrete participant may become ready in `SHIFT.NativeRuntimeState/1`.

## Runtime observation contract

The input runtime observation is:

`SHIFT.NativePhysicsParticipantObservation/1`.

It records three independent views of the same runtime moment.

### Manager-registry view

Required fields include:

- manager global `DAT_00c109e0`;
- observed participant pointer token;
- concrete registry index;
- exact registry-index source `PhysicsParticipant+0x3c`;
- source offset `0x3c`;
- participant descriptor type `3`.

### Selector view

Required fields include:

- selector global `DAT_00bbc600`;
- candidate ready field `+0x74`;
- observed ready value `0`.

### IGPhaseVehicle view

Required fields include:

- observed selected participant pointer token;
- selector ordinal;
- participant process state;
- pointer slot `IGPhaseVehicle+0x450`;
- ordinal slot `IGPhaseVehicle+0x454`;
- state slot `IGPhaseVehicle+0x45c`.

The runtime observation must independently assert that the manager-registry
identity and IGPhaseVehicle selected-pointer identity were both observed.

## Exact join rule

The manager-registry participant pointer token must equal the selected
IGPhaseVehicle pointer token.

That pointer equality proves that both observations refer to one participant
instance. The pointer token is provenance only; `native_runtime` never
dereferences it.

The integer domains are deliberately not joined:

```text
participant_registry_index != selector_ordinal   (no equivalence claim)
```

The output explicitly records:

`registry_index_equals_selector_ordinal = false`.

Even if a retail capture happens to show numerically equal values, that numeric
coincidence is not used as identity evidence.

## Promoted contract

The output is:

`SHIFT.NativePhysicsParticipantRuntimeEvidence/1`.

It revalidates the complete Phase 605 structural boundary and promotes only:

- `participant_instance_ready = true`;
- `registry_selector_identity_join_proven = true`;
- observed participant registry index;
- observed selector ordinal;
- observed participant process state.

Legacy Phase 602 aliases remain disabled:

- `participant_index = -1`;
- `participant_mode = -1`.

Provider identity, PhysX class identity and numerical physics equivalence all
remain false/unassigned.

## Native runtime

The existing `--participant-boundary FILE` option now admits two distinct
contracts:

1. `SHIFT.NativePhysicsParticipantBoundary/1`
   - structural-only;
   - participant not ready;
   - registry/selector/process values remain `-1`.
2. `SHIFT.NativePhysicsParticipantRuntimeEvidence/1`
   - exact runtime instance join proven;
   - participant ready;
   - registry index, selector ordinal and process state transported separately.

The common manager/selector ABI checks remain identical in both modes.

## CI

Linux Vulkan CI preserves the Phase 605 structural regression:

- three fixed steps;
- topology steps = 3;
- ready steps = 0;
- unresolved steps = 3;
- registry index = -1;
- selector ordinal = -1.

A second synthetic runtime-observation fixture uses:

- one pointer token `0x12345678`;
- registry index `7`;
- selector ordinal `2`;
- process state `1`.

The five-step deterministic input smoke then requires:

- participant ready = true;
- identity join proven = true;
- registry index = 7;
- selector ordinal = 2;
- topology steps = 5;
- ready steps = 5;
- unresolved steps = 0;
- legacy participant index/mode remain `-1`.

This fixture validates the contract only. It is not authentic retail participant
capture evidence.

## Boundary after Phase 607

A concrete participant can now be transported into the native fixed-step state
without collapsing the manager-registry and selector identity domains.

The next safe physics integration step is to combine an authentic Phase 607
runtime participant observation with a Phase 606 prepared provider-absent
solver frame. That scheduler join must still require exact provider-absent,
matrix/RHS, reset-selection and sparse-graph evidence and must not invent
`FUN_007b4110` post-solve body-state semantics.
