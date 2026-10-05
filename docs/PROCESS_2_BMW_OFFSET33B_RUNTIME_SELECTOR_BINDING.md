# Process 2 — BMW `offset33b` runtime selector binding

## Playable-slice blocker removed

Process 1 contract `SHIFT.BMWOffset33bSelectorCompleteNumeric/1` proves the
complete BMW M3 E36 first-bootstrap BODY0-to-outer-Vehicle numeric family for
all source-backed race-mode selector combinations:

```text
use_drift_cgheight_scale : false/true
Player Difficulty        : 0, 1, 2
```

It deliberately does not choose one row for a native session. This Process 2
step closes that handoff without recomputing retail physics algebra.

New contract:

```text
SHIFT.BMWOffset33bRuntimeSelectorBinding/1
```

Implementation:

```text
src/runtime/bmw_offset33b_runtime_selector.py
```

## Boundary

The selector binder accepts exactly one session selector pair and requires the
upstream proof to contain exactly six unique selector rows covering the Cartesian
product `{normal, drift} x {0,1,2}`. It rejects difficulty index 3 even though
the underlying PhysicsTweaker vectors contain a fourth element.

For the selected row it validates:

- a finite 4x4 row-vector affine matrix;
- the already-proven identity BODY0-to-outer rotation basis;
- exact agreement between matrix translation and the row's explicit translation;
- positive upstream numeric selector-family readiness;
- continued negative `outer Vehicle -> VHF` readiness.

The output promotes only session-local readiness:

```text
race_mode_selector_bound_to_native_bootstrap = true
BMW_numeric_offset33b_ready_for_bound_session = true
BODY0_to_outer_vehicle_root_numeric_matrix_ready_for_bound_session = true
```

It does **not** promote:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready                 = false
vehicle_world_transform_ready                = false
```

## Exact current BMW translations

The six admitted selector pairs collapse to three numeric translations:

```text
normal, difficulty 0/1:
(0, -0.004956085581085581..., -0.011470862470862471...)

normal, difficulty 2:
(0, +0.000689602064602065..., -0.011470862470862471...)

drift, difficulty 0/1/2:
(0, -0.018129356754356754..., -0.011470862470862471...)
```

These values are consumed from Process 1 evidence; Process 2 does not derive or
hard-code the retail COM/CG formula independently.

## CLI

Example source-backed selector binding:

```bash
python3 src/runtime/bmw_offset33b_runtime_selector.py \
  evidence/bmw_offset33b_selector_complete_numeric.json \
  --player-difficulty 1 \
  --normal \
  --json-out out/bmw_offset33b_runtime_selector_binding.json
```

The next integration step is to make `SHIFT.NativeVerticalSliceProfile/1`
consume this bound-session contract and transport its matrix into the native
persistent-vehicle bootstrap. The remaining independent semantic blocker is the
outer-Vehicle-root to VHF vehicle-root frame join.
