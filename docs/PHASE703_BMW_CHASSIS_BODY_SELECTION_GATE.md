# Phase 703 — BMW chassis BODY selection continuity gate

## Playable-slice blocker reduced

Process 1 PR #1188 proves the retail BMW main/chassis BODY structurally:

```text
main_chassis_BODY_selected = true
main_chassis_BODY_index = 0
```

Process 2 Phase 702 already carries that identity together with the exact wheel
and spindle BODY indices.  Phase 698/700 can already select and export a
persistent BODY pose once `VehicleBodyIdentitySelection.selection_proven` is
true.

The only remaining identity edge on that path is still:

```text
*record + 0x340 update child
  -> FUN_007615c0 vehicle solver base
```

Process 1 has not yet proved this pointer continuity.  Phase 703 removes the
manual bridge around that single blocker without pretending it is solved.

## Contract

```text
SHIFT.NativeBMWChassisBodySelectionGate/1
```

Native implementation:

```text
native_runtime/include/shift_bmw_chassis_body_selection_gate.hpp
native_runtime/src/bmw_chassis_body_selection_gate.cpp
```

The gate consumes:

```text
canonical Phase 702 BMW topology
+ ProvenUpdateChildVehicleSolverBaseContinuity
```

and only when `continuity.proven == true` emits:

```text
VehicleBodyIdentitySelection {
    selection_proven = true,
    body_index = 0,
}
```

That output is the existing Phase 698 selector input, so no second pose-selection
ABI is introduced.

## Current fail-closed frontier

The canonical Phase 702 topology still records:

```text
update_child_to_vehicle_solver_base_continuity_proven = false
vehicle_body_selection_ready = false
```

Phase 703 requires those current upstream values to remain unchanged.  A topology
that self-promotes either value is rejected as drift.  The missing positive proof
must arrive through the separate typed continuity input.

Therefore the current repository does **not** emit a positive retail BMW chassis
selection through Phase 703.

The native/Python regressions use `continuity.proven=true` only as a synthetic
future-proof transport test.  They explicitly record that this is not retail
proof.

## End-to-end positive transport already prepared

With synthetic positive continuity, the native regression executes the complete
already-implemented handoff:

```text
Phase 702 canonical BMW topology
-> Phase 703 continuity gate
-> Phase 698 VehicleBodyIdentitySelection(BODY 0)
-> Phase 700 NativeRuntimeState persistent pose handoff
-> SelectedVehicleBodyPose(BODY 0)
```

It verifies that BODY 0 origin/basis are read unchanged and that no persistent
runtime state or counters are mutated by the read-only selection/handoff path.

Thus a future positive Process 1 continuity proof requires replacing only the
proof input; it does not require redesigning the native pose path.

## Rear axle remains separate

The exact SDF identity of the semantic `vehicle+0x2e00 rear_axle` field is still
unknown.  Phase 702 keeps that as a fail-closed input to the existing
`FUN_00757d2c` relation-state dispatcher.

Process 1 PR #1188 proves that rear-axle identity is not required to select the
central chassis BODY.  Phase 703 therefore does not couple the two blockers.

## Process 3 Phase 644 sync

Process 3 PR #1191 / Phase 644 now provides a one-command source-backed
Silverstone + canonical BMW scene bootstrap and preserves durable renderer-side
vehicle identity.  It deliberately does not consume Phase 700 persistent BODY
pose or claim a dynamic vehicle transform.

This means the cross-process chain is now prepared on both sides:

```text
physics side:
  proven chassis BODY 0
  -> [continuity blocker]
  -> Phase 698/700 pose

renderer side:
  retail corpus
  -> Phase 644 playable scene bootstrap
  -> durable BMW renderer subgroup identity
```

Phase 703 does not cross the remaining transform-convention gap.

## Preserved negative boundaries

Phase 703 does not claim or implement:

- `*record+0x340 -> FUN_007615c0` continuity;
- automatic `fixed_step()` scheduling of the deep vehicle update;
- a BODY origin/basis -> SVWT/world-matrix convention;
- per-frame mutation of the Phase 644 BMW renderer subgroup;
- camera follow;
- a retail `rear_axle` BODY index;
- new runtime capture or original-game execution.

## Regression coverage

Python:

```text
src/physics/bmw_chassis_body_selection_gate_runtime.py
tests/test_bmw_chassis_body_selection_gate_runtime.py
```

verifies exact canonical topology, current continuity rejection, synthetic BODY 0
selection, and topology self-promotion rejection.

Native:

```text
shift_runtime_bmw_chassis_body_selection_gate_check
```

verifies the same gate and then feeds the synthetic positive result into the real
Phase 700 `NativeRuntimeState` handoff.

## Next blocker

The next useful Process 1 proof is singular:

```text
*record + 0x340
-> active update child
-> FUN_007615c0 vehicle solver base
```

Once that is positive, Phase 703 can admit the retail BODY 0 selection and Phase
700 can expose its persistent pose.  The next cross-process blocker after that is
then the exact BODY origin/basis -> renderer SVWT/world-transform convention.
