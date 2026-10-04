# Phase 703 — global vehicle BODY-owner selection handoff

## Playable-slice blocker reduced

The original Phase 703 gated BMW chassis BODY 0 on historical
`*record+0x340 -> vehicle solver base` equality. Process 1 PR #1196 supersedes
that model with `SHIFT.GlobalVehicleBodyOwnerIdentity/1`, composing the proven
global outer receiver, the `FUN_00765470 -> FUN_007b2270` BODY-owner receiver
provenance, and the structurally proven BMW chassis BODY 0.

This rewrite removes the obsolete pointer-equality proof boundary and consumes
the composed Process 1 handoff directly. No original `SHIFT.exe` execution and
no new runtime capture are used.

## Native contract

```text
SHIFT.NativeGlobalVehicleBodyOwnerSelection/1
```

Implementation:

```text
native_runtime/include/shift_global_vehicle_body_owner_selection.hpp
native_runtime/src/global_vehicle_body_owner_selection.cpp
```

The native handoff mirrors only the fields required by Phase 698/700:

```text
outer_receiver_to_BODY_owner_continuity_proven
vehicle_BODY_selection_ready
selected_BODY_index
phase698_positive_selection_admissible
phase700_runtime_handoff_admissible
phase703_update_child_equality_gate_required
phase703_gate_rewrite_ready
```

All positive readiness flags must move together. The obsolete update-child gate
must remain false. A blocked handoff may not preclaim a BODY index. A positive
handoff is accepted only for the proven retail BMW chassis `BODY 0`, then emits
the existing Phase 698 `VehicleBodyIdentitySelection` ABI and reuses the Phase
700 runtime handoff.

## Current retail state remains fail-closed

Process 1 #1196 records that the repository still lacks the targeted retail
`SHIFT.GhidraFunctionInstructions/2` export for `FUN_00765470`; therefore its
composed identity is not yet positive for retail execution.

Current state remains:

```text
outer_receiver_to_BODY_owner_continuity_proven = false
vehicle_BODY_selection_ready = false
selected_BODY_index = null
phase698_positive_selection_admissible = false
phase700_runtime_handoff_admissible = false
phase703_update_child_equality_gate_required = false
```

Phase 703 rejects this before Phase 700 reads runtime pose state. Synthetic
all-positive fixtures exist only to regress the future transport and are not
retail proof.

## End-to-end transport prepared

```text
SHIFT.GlobalVehicleBodyOwnerIdentity/1
-> Phase 703 validation
-> Phase 698 VehicleBodyIdentitySelection(BODY 0)
-> Phase 700 NativeRuntimeState persistent pose handoff
-> SelectedVehicleBodyPose(BODY 0)
```

The native regression verifies BODY 0 origin/basis are read unchanged and that
BODY bytes, snapshot generation and explicit-update count are not mutated.

## Process 3 Phase 645/646 sync

Phase 645 proves the canonical BMW VHF vehicle-root/body-MEB static bind
transform and exact VHF column-vector -> SVWT row-vector conversion. Phase 646
then adds the native dynamic vehicle transform transport core plus authoritative
`source_group=vehicle` draw-group targeting.

Neither phase invents the missing dynamic physics composition. After a positive
retail BODY-owner identity, the remaining cross-process blocker is narrowly:

```text
persistent BODY0 pose frame
-> exact BODY0/VHF bind-frame composition
-> Phase 646 dynamic transform transport
-> vehicle draw-group SVWT update
```

Renderer object rediscovery and transport plumbing are no longer blockers.

## Preserved negative boundaries

Phase 703 does not claim:

- positive retail `FUN_00765470` BODY-owner receiver proof;
- `*record+0x340 == 0x00c13700`;
- a retail `rear_axle` BODY index;
- BODY0 pose -> VHF/SVWT composition;
- camera follow;
- automatic deep-physics `fixed_step()` scheduling.

## Regression coverage

Python `src/physics/global_vehicle_body_owner_selection_runtime.py` and
`tests/test_global_vehicle_body_owner_selection_runtime.py` check blocked retail
admission, transactional readiness flags, BODY-index preclaim rejection,
obsolete-gate rejection and exact BODY 0 synthetic transport.

Native `shift_runtime_global_vehicle_body_owner_selection_check` verifies the
blocked handoff is rejected before Phase 700 runtime reads and exercises a
synthetic positive Process 1 handoff through the real Phase 700 runtime path.

## Next blocker

Immediate upstream work remains:

```text
retail FUN_00765470 instruction export
-> prove entry ECX reaches FUN_007b2270 as BODY-array owner ECX
-> positive SHIFT.GlobalVehicleBodyOwnerIdentity/1
-> Phase 703/698/700 retail BODY0 pose
```

After that, Process 2 should consume the BODY0 pose into the exact Phase 645
bind-frame composition required by Phase 646 rather than revisiting update-child
identity.
