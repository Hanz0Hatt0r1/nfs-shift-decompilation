# Phase 705 — BMW vehicle world-matrix runtime handoff

## Playable-slice blocker reduced

Phases 703, 700 and 704 already contain the three separate pieces needed before
renderer transport:

```text
Process 1 global BODY-owner identity
-> Phase 703 identity admission
-> Phase 700 read-only persistent BODY0 pose
-> Phase 704 BODY0/VHF composition
-> Phase 646 VehicleWorldMatrix ABI
```

Before Phase 705 a caller still had to assemble those steps manually. That left
an unnecessary integration gap in the exact path that will eventually run once
the remaining Process 1 proofs become positive.

Phase 705 provides one read-only, fail-closed native handoff from
`NativeRuntimeState` plus the existing typed proof inputs to the Phase 646 matrix
ABI. It introduces no new physics arithmetic or transform semantics.

No original `SHIFT.exe` execution and no new runtime capture are used.

## Contract

```text
SHIFT.NativeBMWVehicleWorldMatrixRuntimeHandoff/1
```

Implementation:

```text
native_runtime/include/shift_bmw_vehicle_world_matrix_runtime_handoff.hpp
native_runtime/src/bmw_vehicle_world_matrix_runtime_handoff.cpp
```

The public operation is:

```text
NativeRuntimeState
+ GlobalVehicleBodyOwnerIdentityHandoff
+ ProvenBmwVhfBindFrame
+ ProvenBmwBody0BindFrame
-> BmwVehicleWorldMatrixRuntimeHandoffResult
```

The result transports:

```text
SelectedVehicleBodyPose
BODY0 runtime row matrix
VehicleWorldMatrix
runtime BODY count
explicit outer-update count
```

## No duplicate gates

Phase 705 deliberately delegates every decision to the already-proven boundary
that owns it.

### Identity

```text
build_global_vehicle_body_pose_runtime_handoff(...)
```

reuses Phase 703 and Phase 700. Therefore:

- current blocked retail `SHIFT.GlobalVehicleBodyOwnerIdentity/1` is rejected;
- obsolete update-child pointer equality remains forbidden;
- participant/runtime admission is still enforced by Phase 700;
- BODY0 selection is not reimplemented.

### Transform composition

```text
compose_bmw_body0_pose_to_vehicle_world_matrix(...)
```

reuses Phase 704 unchanged. Therefore:

- Phase 645 VHF bind proof remains required;
- positive, proven-static `SHIFT.BMWBody0BindFrameProof/1` remains required;
- exact multiplication order stays
  `VHF_bind * inverse(BODY0_bind) * BODY0_runtime`;
- no identity-bind or axis-remap assumption is introduced;
- the output remains the Phase 646 float32 `VehicleWorldMatrix` ABI.

Phase 705 contains no matrix inversion, multiplication, trig, sqrt or recovered
machine-scalar arithmetic of its own.

## Fail-closed ordering

The integration order is intentional:

```text
Phase 703 identity admission
-> Phase 700 runtime state / pose admission
-> Phase 704 bind proofs + composition
```

A currently blocked retail identity is therefore rejected before uninitialized
runtime pose state is inspected. Once identity is admitted, Phase 700 remains the
owner of participant/cardinality/generation checks. Only an admitted selected
pose reaches Phase 704.

All three operations are read-only with respect to the persistent runtime state.

## Current retail status

Process 1 PR #1196 still keeps the global BODY-owner identity blocked until the
targeted retail `FUN_00765470` instruction/receiver proof is committed.

Process 1 PR #1200 narrows the separate BODY0 bind-initialization search to a
finite caller/callsite worklist around:

```text
FUN_007b6900
FUN_007b3670
FUN_007b7840 + direct callers
```

but explicitly keeps:

```text
BODY0_pointer_identity_proven        = false
origin_basis_value_provenance_proven = false
BODY0_bind_matrix_proven             = false
```

Therefore Phase 705 is currently reusable integration infrastructure, not a
positive retail world-matrix producer.

## Regression coverage

### Python oracle

```text
src/physics/bmw_vehicle_world_matrix_runtime_handoff_runtime.py
tests/test_bmw_vehicle_world_matrix_runtime_handoff_runtime.py
```

The oracle composes the existing Phase 703 and Phase 704 Python contracts and
checks:

- current retail identity rejection;
- exact BODY0 selection agreement;
- Phase 704 bind gate preservation;
- exact non-commuting world matrix from the existing fixture;
- current retail/world-renderer boundaries remain false.

### Native regression

```text
shift_runtime_bmw_vehicle_world_matrix_runtime_handoff_check
```

The native test verifies:

1. blocked retail identity rejects before Phase 700 reads an uninitialized
   runtime state;
2. synthetic positive identity still cannot bypass Phase 700 persistent-state
   admission;
3. after normal `NativeRuntimeState` initialization, the selected BODY0 pose is
   transported unchanged;
4. the final matrix exactly equals a direct call to Phase 704 on that selected
   pose;
5. missing BODY0 bind proof remains rejected;
6. success and failure paths do not mutate BODY bytes, pose snapshots,
   snapshot generation or explicit-update telemetry.

## Preserved boundaries

Phase 705 does **not**:

- make Process 1 retail BODY-owner identity positive;
- create a BODY0 bind-frame proof;
- write Phase 646 output into live Vulkan buffers;
- enable camera follow;
- attach the explicit deep outer update to `fixed_step()`;
- replace any of the nine Phase 699/701 external providers;
- reinterpret Phase 645 static bind data as a dynamic pose.

## Next blocker

The Process 2 transport path is now ready end-to-end up to the two missing
upstream proofs:

```text
positive retail global BODY-owner identity
+ positive BODY0 bind-frame proof
-> Phase 705 NativeRuntimeState -> VehicleWorldMatrix
-> Phase 646 dynamic transform transport
-> Process 3 live Vulkan vehicle-buffer wiring
```

Until those proofs exist, Process 2 should keep this path explicit and
fail-closed rather than manufacture a retail transform.
