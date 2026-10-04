# Phase 704 — BMW BODY0 -> VHF vehicle world-matrix composition

## Playable-slice blocker reduced

Process 1 PR #1199 / `SHIFT.BMWBody0VHFBindFrameFrontier/1` freezes the exact
row-vector composition required to turn the persistent chassis BODY0 pose into
the vehicle world matrix consumed by Process 3 Phase 646:

```text
M_object_world = M_vhf_bind * inverse(M_BODY0_bind) * M_BODY0_runtime
```

The formula is now proven; one retail static witness is still missing:

```text
M_BODY0_bind : BODY0-local -> VHF vehicle-root at bind/assembly time
```

Phase 704 ports only the proven composition into native code. It does not assume
that witness is identity, does not infer a BODY/MEB axis remap, and does not
promote the current retail path to ready.

No original `SHIFT.exe` execution and no new runtime capture are used.

## Native contract

```text
SHIFT.NativeBMWBody0VHFWorldMatrixComposition/1
```

Implementation:

```text
native_runtime/include/shift_bmw_body0_vhf_world_matrix_composition.hpp
native_runtime/src/bmw_body0_vhf_world_matrix_composition.cpp
```

Inputs are deliberately typed proof boundaries:

```text
SelectedVehicleBodyPose
  <- existing Phase 703 -> Phase 698 -> Phase 700 path

ProvenBmwVhfBindFrame
  <- Process 3 Phase 645 canonical BMW VHF body-MEB bind transform

ProvenBmwBody0BindFrame
  <- future positive SHIFT.BMWBody0BindFrameProof/1
```

`ProvenBmwBody0BindFrame` requires:

- ready proof;
- `evidence_proven_static = true`;
- BODY index exactly `0`;
- `identity_matrix_assumed = false`;
- finite, non-singular D3D row-vector affine matrix.

The selected runtime pose must also be BODY0 and have finite origin/basis with a
non-singular basis.

## Exact frame conversion

The persistent BODY snapshot carries:

```text
origin : f64 x3
basis  : f32 x9, source-backed row-major B
```

The proven BODY equation is column-vector form:

```text
world_offset_column = B * local_column
```

Therefore Phase 704 constructs the D3D row-vector runtime matrix by the exact
homogeneous transpose frozen by Process 1 #1199:

```text
b0 b3 b6 0
b1 b4 b7 0
b2 b5 b8 0
ox oy oz 1
```

No axis swap, sign flip or inferred local-frame equivalence is inserted.

## Arithmetic and precision boundary

The bind inverse and two 4x4 multiplications are evaluated in `double` in the
same explicit source order as the Process 1 reference contract:

```text
(VHF bind * inverse(BODY0 bind)) * BODY0 runtime
```

The result is narrowed once to the existing Phase 646 ABI:

```text
VehicleWorldMatrix = std::array<float, 16>
```

The narrowing is checked for overflow/non-finite output and the resulting
float32 matrix is revalidated as finite, non-singular D3D row-vector affine.
This is a native renderer-transport boundary, not a recovered x87 scalar path;
Phase 692 sqrt/trig machine boundaries remain untouched.

## Phase 646 compatibility

The native regression compiles the Phase 646 transport source alongside the
Phase 704 composition and runs the resulting matrix through:

```text
validate_vehicle_world_matrix(...)
apply_vehicle_world_transform(...)
```

using immutable object-space geometry. A non-commuting affine fixture proves the
matrix order; the expected final matrix is:

```text
 0   1   0    0
-1   0   0    0
 0   0  0.5   0
14  22  34    1
```

and object-space point `(1,2,3)` becomes `(12,23,35.5)` through the existing
Phase 646 core.

This proves transport compatibility only. It does not enable live Vulkan vertex
buffer mutation; Process 3 still owns that mechanical renderer wiring.

## Current retail state remains fail-closed

Process 1 #1199 records both upstream blockers explicitly:

1. current retail `SHIFT.GlobalVehicleBodyOwnerIdentity/1` is still blocked on
   the targeted `FUN_00765470` instruction export/receiver proof;
2. `BODY0_bind_frame_proven = false` because no positive
   `SHIFT.BMWBody0BindFrameProof/1` is committed.

Therefore Phase 704 currently provides reusable native infrastructure, not a
retail world-matrix producer.

Synthetic positive matrices in regressions are transport fixtures only and are
not retail evidence.

## Fail-closed behavior

Phase 704 rejects before emitting a matrix on:

- missing Phase 645 VHF proof;
- missing/non-static BODY0 bind proof;
- BODY index other than 0;
- an identity-bind assumption flag;
- NaN/Inf origin, basis or bind data;
- non-affine homogeneous layout;
- singular BODY runtime basis or bind matrix;
- float32 overflow/non-finite narrowing.

It changes no BODY bytes, snapshot generation, outer-update count, provider
ordering or scheduling.

## Python oracle

```text
src/physics/bmw_body0_vhf_world_matrix_composition_runtime.py
tests/test_bmw_body0_vhf_world_matrix_composition_runtime.py
```

The test imports the merged Process 1 #1199 builder and compares Phase 704's
non-commuting fixture directly against
`compose_body0_pose_to_vhf_world_matrix(...)`, catching multiplication-order or
basis-transpose drift.

## Native regression

```text
shift_runtime_bmw_body0_vhf_world_matrix_composition_check
```

It checks:

- exact non-commuting composition result;
- Phase 646 matrix validation and transform execution;
- missing bind proof rejection;
- identity-assumption rejection;
- wrong BODY rejection;
- singular matrix rejection;
- non-finite pose rejection.

## Preserved boundaries

Phase 704 does **not**:

- make `SHIFT.GlobalVehicleBodyOwnerIdentity/1` retail-ready;
- create `SHIFT.BMWBody0BindFrameProof/1`;
- assume BODY0-local == VHF/MEB-local;
- mutate Vulkan buffers or renderer draw state;
- enable camera follow;
- attach the explicit deep outer update to `fixed_step()`;
- replace any of the nine Phase 699/701 external physics providers.

## Next blocker

The semantic transform chain is now prepared up to one missing static witness:

```text
positive retail BODY0 pose
+ positive BODY0 bind-frame proof
+ Phase 645 VHF bind
-> Phase 704 proven world matrix
-> Phase 646 dynamic transform transport
-> Process 3 live Vulkan vehicle-buffer wiring
```

Until Process 1 closes the BODY0 bind witness and retail BODY-owner admission,
Process 2 must remain fail-closed rather than substitute identity or inferred
frame equivalence.
