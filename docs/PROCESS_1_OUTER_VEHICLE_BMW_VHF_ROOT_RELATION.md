# Process 1 — exact outer Vehicle -> BMW VHF root relation

## BLOCKER

**Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

It closes the semantic identity-vs-affine edge between the persistent outer
Vehicle root and the canonical BMW VHF `HIERARCHY Root`. That is the last frame
meaning needed before numeric BODY0-local -> VHF-root composition.

## INPUT

- `SHIFT.OuterVehicleRenderRootDeltaProvenance/1` (exact entry-ECX stores and terminal value roots);
- `SHIFT.OuterVehicleRenderSnapshotAffineBridge/1`;
- `SHIFT.VehicleRenderModelRootAffineDomainJoin/1` (PR #1330);
- `SHIFT.BMWVHFHierarchyRootFrame/1` (PR #1323).

The exact retail setup chain additionally anchors the delta lifetime:

```text
MWL::Core::PhysicsParticipant::Restart / FUN_0074ddc3
  0x0074de12 -> MWL::Core::Vehicle::InitVehicle / FUN_00798df0
  0x007990ed -> FUN_00795d60
                  -> outerVehicle +0x19c/+0x1a0/+0x1a4
```

Thus the delta is setup state, not the per-frame vehicle pose.

## OUTPUT

`SHIFT.OuterVehicleBMWVHFRootRelation/1` proves a **setup-fixed affine** relation: fixed for an initialized vehicle instance with respect to per-frame outer pose, not asserted as one global constant across all vehicle/config selections.
Using the established D3D row-vector convention:

```text
M_model_to_world = T(delta_local) * M_outer_to_world
M_vhf_root_to_world = M_vhf_root_to_model * T(delta_local) * M_outer_to_world
```

Therefore:

```text
M_vhf_root_to_outer = M_vhf_root_to_model * T(delta_local)
M_outer_to_vhf_root = inverse(M_vhf_root_to_model * T(delta_local))
```

where:

```text
delta_local = outerVehicle[+0x19c,+0x1a0,+0x1a4]
```

This is not an identity proof. An identity-valued VHF root matrix does not erase
the independently proven `T(delta_local)` term, and even a numerically identity
final matrix must not be promoted to identity semantics without separate
provenance.

## CONSUMER

1. Process 1 numeric BMW BODY0 bind-frame composition.
2. Process 2 relation admission after the selected BMW setup materializes the
   three delta scalars into a finite 16-scalar matrix.

## GATES_CHANGED

```text
outer_vehicle_root_to_VHF_vehicle_root_ready       = true
outer_vehicle_root_to_VHF_fixed_affine_delta_ready = true
```

Still false:

```text
outer_vehicle_root_to_VHF_relation_numeric_matrix_ready
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready
BODY0_bind_frame_proof_ready
vehicle_world_transform_ready
```

## LIMITS

- No BMW delta number is guessed from naming, visual alignment, or an identity
  VHF root matrix.
- PR #1329 Process 2 numeric admission remains fail-closed because it requires a
  finite 16-scalar relation matrix.
- No rejected car-body `+0x34/+0x534`, render-manager `+0xca4`, or
  `FUN_007b7840` branch is reopened.
- No runtime capture or original-game execution is used.

## TESTS

`tests/test_ghidra_outer_vehicle_bmw_vhf_root_relation.py` checks exact delta-value-root admission, symbolic fixed-affine promotion, row-vector composition order, pure numeric algebra evaluation with proof gates still closed, identity non-promotion, runtime-pose rejection, model-domain drift, root parent-chain drift, missing terminal-root rejection, and upstream semantic-preclaim rejection. Focused result: 8/8 passed.

## NEXT_OWNER

Process 1: materialize the selected BMW `Vehicle::InitVehicle` delta values from
exact setup inputs, evaluate `M_outer_to_vhf_root`, then compose the already
positive numeric BODY0->outer matrix into `SHIFT.BMWBody0BindFrameProof/1`.
