# Phase 651 — playable camera-follow source frontier

## Playable-slice blocker reduced

The native runtime already executes the recovered CameraManager snapshot and
guarded double-buffer transition. It can also ingest the recovered numeric
CameraManager state through `SHIFT.NativeCameraStateBridge/1`. The remaining
playable-slice camera blocker is not generic camera state transport: it is the
retail source object and timing relation that makes the gameplay camera follow
the current vehicle.

Phase 651 turns that broad blocker into a finite, machine-readable proof
frontier:

```text
SHIFT.CameraFollowSourceFrontier/1
```

The frontier does **not** enable camera follow. It records the strongest current
source-backed candidate and the exact static joins still required before Process
2 may connect the current retail `VehicleWorldMatrix` to the native camera.

## Existing recovered source lanes

The recovered CameraManager controller paths already distinguish four source
lanes:

| Mode | Source | Activation | Current Phase 651 role |
| ---: | --- | --- | --- |
| 1 | `active_buffer+0x20` | `FUN_0080de00` / `FUN_0080dfd0` | static/sub-view lane |
| 2 | `active_buffer+0x1ca0`, stride `0x460` | `FUN_0080e0d0` | follow **candidate only** |
| 3 | `active_buffer+0x17a0`, stride `0x280` | `FUN_0080e140` | static-camera lane |
| 4 | caller-supplied source | `FUN_0080d520` | external-source lane |

Mode 2 is the narrowest source-backed candidate because its activation performs:

```text
active_buffer+0x1ca0 source
  -> source.vtable+0x90(runtime_argument)
  -> FUN_0080d300(..., source, ...)
  -> CameraManager+0x2568 = source
  -> source+0x44 = CameraManager
  -> source.vtable+0x64()
```

The repository historically calls this the tracking source lane, but that label
is **not** promoted into proof that the source follows the selected BMW/player
vehicle.

## Exact Process 1 requests

Phase 651 replaces the vague `camera follow source` blocker with four proof
requests:

1. **Mode-2 runtime argument identity** — trace every retail callsite and producer
   of the `runtime_argument` passed to `FUN_0080e0d0`; prove or reject identity /
   ownership with the selected retail player vehicle.
2. **Mode-2 concrete source vtable** — prove the actual object/vtable installed at
   `active_buffer+0x1ca0` and resolve vtable entries `+0x90` and `+0x64`.
3. **Vehicle-pose dependency** — trace those resolved callees and prove how the
   selected vehicle/current pose reaches camera source state. Similarity to the
   reconstructed native matrix is not sufficient.
4. **Update ordering** — prove the retail freshness/order relation between the
   vehicle update and mode-2 camera-source update.

Only after all four are positive may Process 2 wire the current retail vehicle
transform into camera-follow execution.

## Vehicle-transform gate

The optional input to the Phase 651 builder is the existing Phase 705 contract:

```text
SHIFT.NativeBMWVehicleWorldMatrixRuntimeHandoff/1
```

The current contract proves the retail BODY identity but still keeps:

```text
current_retail_BODY0_bind_ready     = false
current_retail_world_matrix_ready   = false
```

Phase 706/649 already provide persistent/freshness-checked transform transport
and the Vulkan sink. Phase 651 does not reinterpret that infrastructure as a
positive current retail matrix or as camera timing proof.

A future positive Phase 705 world-matrix contract still cannot make Phase 651
ready by itself: the camera source/vtable/timing proofs remain independent.

## CLI

```bash
python3 tools/build_camera_follow_source_frontier.py \
  --json-out out/camera_follow_source_frontier.json
```

To include the current Phase 705 gate state:

```bash
python3 tools/build_camera_follow_source_frontier.py \
  --vehicle-world-matrix-handoff out/bmw_vehicle_world_matrix_runtime_handoff.json \
  --json-out out/camera_follow_source_frontier.json
```

The tool exits successfully when it has built the frontier; `ready=false` is an
evidence state, not a CLI failure.

## Native admission boundary

Until the positive contracts exist, Phase 651 fixes these values false:

```text
native_camera_follow_ready
may_bind_vehicle_transform_to_camera_source
may_schedule_camera_after_vehicle_update
may_serialize_opaque_word0_as_native_pointer
```

It also refuses to claim:

- that mode 2 is already the BMW/player follow camera;
- that the opaque CameraManager word 0 may be converted into a native pointer;
- a source vtable by layout similarity;
- retail camera math from the current native camera defaults;
- retail cadence from the host/native fixed `1/60` loop;
- Phase 706 freshness transport as proof of retail camera scheduling.

## Regression coverage

`tests/test_camera_follow_source_frontier.py` freezes:

- the four recovered source lanes;
- the exact mode-2 `+0x90` / `FUN_0080d300` / `+0x64` chain;
- the four Process 1 proof requests;
- the current negative Phase 705 BODY0/world-matrix gates;
- invalid transform-contract rejection;
- fail-closed behavior even with a hypothetical positive world matrix.

## Result

The camera blocker is now finite and independent of renderer transport. The next
camera work is no longer `reverse engineer the camera`; it is the exact mode-2
source identity/vtable/vehicle-pose/update-order proof. Until that proof is
positive, Process 2 has no permission to attach the native vehicle transform to
CameraManager source state.
