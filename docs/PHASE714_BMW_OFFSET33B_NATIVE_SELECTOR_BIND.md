# Phase 714 — BMW `offset33b` native selector bind

## Playable-slice blocker reduced

Process 1 PR #1276 proves a selector-complete numeric family for the BMW
`BODY0-local -> outer Vehicle-root` bind, but deliberately leaves the singular
matrix false until Process 2 binds a race-mode selector pair.

Phase 714 consumes exactly that boundary. It does not infer a new resource
value and it does not promote the independent outer Vehicle-root -> VHF
vehicle-root relation.

Native contract:

```text
SHIFT.NativeBMWOffset33bSelector/1
```

Implementation:

```text
native_runtime/include/shift_bmw_offset33b_native_selector.hpp
native_runtime/src/bmw_offset33b_native_selector.cpp
```

## Source-backed selector domain

PR #1276 proves that `FUN_007bfbe0` consumes the `RaceModeInfo` selector pair
staged by the retail `ChangeRaceMode` chain:

```text
RaceModeInfo+0x0e -> normal/drift CGHeight-scale branch
RaceModeInfo+0x6c -> Player Difficulty 0..2
```

The admitted domain is therefore:

```text
use_drift_cgheight_scale = false|true
player_difficulty        = 0|1|2
```

The native selector rejects an unbound selector and rejects difficulty values
outside `0..2`.

## Deterministic Silverstone playable policy

The first playable Linux vertical slice is not a replay of one captured retail
session. It needs one deterministic member of the retail-admissible selector
family.

Phase 714 binds:

```text
Silverstone playable branch = normal
Player Difficulty            = 1
```

Difficulty `1` is the source-backed initializer value written by
`FUN_0041a730`. Choosing the normal branch is an explicit native vertical-slice
policy; it is not presented as an observation of a historical retail session.

This selector resolves the PR #1276 family to:

```text
offset33b =
(0,
 +0.004956085581085581085581085581085581...,
 +0.011470862470862470862470862470862471...)

BODY0-local -> outer Vehicle-root translation =
(0,
 -0.004956085581085581085581085581085581...,
 -0.011470862470862470862470862470862471...)
```

The matrix uses the established D3D row-vector affine convention:

```text
[1 0 0 0]
[0 1 0 0]
[0 0 1 0]
[0 y z 1]
```

## Full selector-family preservation

The native bridge retains all source-backed cases instead of hard-coding only
the playable policy:

```text
normal, difficulty 0|1:
  translation.y = -0.004956085581085581...

normal, difficulty 2:
  translation.y = +0.0006896020646020646...

drift, difficulty 0|1|2:
  translation.y = -0.018129356754356754...

all cases:
  translation.x = 0
  translation.z = -0.011470862470862471...
```

That keeps the bridge reusable when a later native UI/profile implementation
changes the selected mode.

## Fail-closed frame boundary

The output type is deliberately named:

```text
BmwBody0OuterVehicleRootBind
```

and contains:

```text
body0_local_to_outer_vehicle_root
```

It is not `ProvenBmwBody0BindFrame`, whose current Phase 704 ABI is already in
VHF vehicle-root space. Phase 714 therefore cannot silently bypass the still
open frame join.

Positive for the deterministic native Silverstone selector:

```text
race_mode_selector_bound_for_native_silverstone = true
BMW_numeric_offset33b_ready                      = true
BODY0_to_outer_vehicle_root_numeric_matrix_ready = true
```

Still fail-closed:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready                 = false
vehicle_world_transform_ready                = false
```

## Regression

The native check covers all six selector combinations plus both rejection paths:

```bash
cmake --build <build> --target shift_runtime_bmw_offset33b_native_selector_check
ctest --test-dir <build> -R shift_runtime_bmw_offset33b_native_selector --output-on-failure
```

The check emits a compact `SHIFT.NativeBMWOffset33bSelector/1` status record.

## Next blocker

With the singular native `BODY0 -> outer Vehicle-root` matrix selected, the
next static/runtime join is exactly:

```text
outer Vehicle-root
  -> VHF vehicle-root / assembly frame
```

Only that join may convert this Phase 714 matrix into the existing Phase 704
VHF-root bind ABI and unblock the persistent BMW vehicle world transform.
