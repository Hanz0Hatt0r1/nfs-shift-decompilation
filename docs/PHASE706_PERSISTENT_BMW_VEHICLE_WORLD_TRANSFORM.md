# Phase 706 — persistent BMW vehicle world-transform state

## Playable-slice blocker reduced

Phase 705 produces a read-only `VehicleWorldMatrix` from the admitted persistent
BODY0 pose and proven bind inputs. Before Phase 706 that matrix existed only as
a return value; no persistent Process 2 runtime state could publish it to a
future renderer/camera consumer while detecting stale physics provenance.

Phase 706 adds a transactional persistent transform session:

```text
Phase 705 admitted world matrix
-> transactional commit
-> persistent vehicle transform + source BODY0 provenance
-> freshness check against current NativeRuntimeState
```

This is reusable infrastructure for the milestone:

```text
multiple explicit physics updates
-> updated persistent BODY0 pose
-> explicit transform recommit
-> current vehicle world transform
```

It does not claim a positive retail BODY-owner identity or BODY0 bind proof and
does not attach any operation to `fixed_step()`.

No original `SHIFT.exe` execution and no new runtime capture are used.

## Contract

```text
SHIFT.PersistentBMWVehicleWorldTransform/1
```

Implementation:

```text
native_runtime/include/shift_persistent_bmw_vehicle_world_transform.hpp
native_runtime/src/persistent_bmw_vehicle_world_transform.cpp
```

`PersistentBmwVehicleWorldTransformState` stores only data produced after a
successful Phase 705 handoff:

```text
ready
BODY index
source runtime BODY count
source pose snapshot generation
source explicit-update count
source BODY0 origin
source BODY0 basis
transform commit generation
Phase 646 VehicleWorldMatrix
```

The state is a Process 2 runtime session rather than a new field inside
`NativeRuntimeState`. This keeps the core runtime free of a renderer-typed value
until the retail transform path is positive, while still giving the executable
a persistent object that can later be owned beside the existing Phase 701
provider session.

## Transactional commit

```text
commit_bmw_vehicle_world_transform(...)
```

first executes the complete Phase 705 read-only handoff. Only after identity,
participant/runtime state, VHF bind and BODY0 bind admission plus world-matrix
composition have all succeeded is a new persistent transform state built and
assigned.

If any upstream boundary throws, the previously committed transform remains
unchanged.

A successful commit increments only native transform telemetry:

```text
commit_generation += 1
```

It does not mutate:

- persistent BODY bytes;
- BODY pose snapshots;
- BODY pose snapshot generation;
- explicit outer-update count;
- input telemetry;
- camera state.

Commit-generation overflow fails closed before publication.

## Freshness / stale rejection

```text
read_current_bmw_vehicle_world_transform(...)
```

returns a transform only when its recorded source still matches the current
`NativeRuntimeState.outer_update` state.

The comparison includes:

- BODY index = 0;
- runtime BODY cardinality;
- BODY pose snapshot generation;
- explicit outer-update count;
- exact stored BODY0 origin;
- exact stored BODY0 basis.

Generation/count checks alone are deliberately insufficient because
`initialize_explicit_outer_update_body_state()` resets both values to zero. A
reinitialize with different BODY bytes must therefore invalidate an old
transform even when telemetry numerically repeats an earlier generation.

This gives renderer/camera consumers a simple rule:

```text
read succeeds -> transform belongs to current persistent BODY0 state
read fails stale -> recompute/recommit after the current explicit physics state
```

## Current retail state remains blocked

Phase 706 does not alter the two upstream Process 1 blockers:

1. `SHIFT.GlobalVehicleBodyOwnerIdentity/1` is not retail-positive until the
   targeted `FUN_00765470` receiver proof is committed;
2. Process 1 PR #1200 narrows BODY0 bind initialization but retains
   `BODY0_bind_matrix_proven = false`.

Therefore current retail code cannot successfully commit a transform. Synthetic
positive identity/bind fixtures are regression-only transport tests.

## Python oracle

```text
src/physics/persistent_bmw_vehicle_world_transform_runtime.py
tests/test_persistent_bmw_vehicle_world_transform_runtime.py
```

It verifies:

- successful commit/read;
- current retail identity rejection;
- failed recommit leaves prior state unchanged;
- stale snapshot generation rejection;
- stale explicit-update count rejection;
- reinitialize with reused zero generation but different BODY0 pose rejection;
- successful recommit increments transform generation only;
- generation overflow rejection.

## Native regression

```text
shift_runtime_persistent_bmw_vehicle_world_transform_check
```

The native test uses the real `NativeRuntimeState` and Phase 705 path. It checks
transactional publication, current reads, both telemetry stale gates, failed
recommit preservation, repeated successful commit, and a real BODY-byte
reinitialize with a changed BODY0 origin while generation/count reset to zero.

## Preserved boundaries

Phase 706 does **not**:

- schedule the deep outer update in `fixed_step()`;
- automatically recompute a transform after physics updates;
- mutate live Vulkan buffers;
- choose a camera follow convention;
- make Phase 646 renderer transport cumulative;
- replace any Phase 699/701 external physics provider;
- weaken Phase 703/704/705 fail-closed proof gates.

## Next blocker

With Phase 706, Process 2 has persistent transform infrastructure ready for the
first positive retail proof:

```text
positive retail BODY-owner identity
+ positive BODY0 bind-frame proof
-> Phase 705 VehicleWorldMatrix
-> Phase 706 persistent current transform
-> Phase 646 renderer transport
-> Process 3 live Vulkan vehicle-buffer wiring
```

After each future explicit physics update, the previous transform becomes stale
by provenance until a new explicit Phase 706 commit succeeds. This preserves the
current scheduling boundary instead of inventing cadence ownership.
