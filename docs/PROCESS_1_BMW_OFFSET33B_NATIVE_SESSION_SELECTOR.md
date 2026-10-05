# Process 1 — bind BMW `offset33b` to the native Silverstone session

## Playable-slice blocker removed

`SHIFT.BMWOffset33bSelectorCompleteNumeric/1` proves the complete retail numeric
family but intentionally leaves a singular matrix fail-closed until a session
selector is supplied:

```text
use_drift_cgheight_scale : bool
player_difficulty        : {0, 1, 2}
```

The native Linux vertical slice is not required to guess an arbitrary retail
live-session state. It owns its own explicit session policy. This phase validates
that policy against the already source-backed retail selector domain and selects
exactly one proven numeric family member.

New contract:

```text
SHIFT.BMWOffset33bNativeSessionSelection/1
```

Tool:

```text
tools/bind_bmw_offset33b_native_session_selector.py
```

Committed target-slice artifact:

```text
evidence/bmw_offset33b_native_silverstone_session.json
```

## Native Silverstone policy

For the first playable slice the project policy is deliberately explicit:

```text
session target      = Silverstone + BMW_M3_E36
physics mode        = normal
Player Difficulty   = 1
```

This is a **native vertical-slice choice**, not an inference that every retail
Silverstone session used these values. `Player Difficulty=1` is within the exact
retail domain proven by the selector-family pass, and `normal` selects the
source-backed `CGHeight Scale` branch rather than `Drift CGHeight Scale`.

The binder refuses any mode outside `{normal, drift}` and any difficulty outside
`{0,1,2}`. It requires the upstream family to contain all six unique selector
pairs and requires each selected BODY0 translation to remain exactly the negative
of `offset33b` in the already-proven D3D row-vector identity-rotation matrix.

## Selected BMW numeric bind

The selected #1275 family row is:

```text
target_CG = (0, 0.168, -0.081)

offset33b =
(0,
 -0.0214366883116883116883116883116883...,
 +0.0114708624708624708624708624708625...)
```

Therefore:

```text
BODY0 -> outer Vehicle translation =
(0,
 +0.0214366883116883116883116883116883...,
 -0.0114708624708624708624708624708625...)
```

and the singular matrix is:

```text
[1 0 0 0]
[0 1 0 0]
[0 0 1 0]
[0 +0.0214366883116883... -0.0114708624708625... 1]
```

The new handoff may therefore set:

```text
native_session_selector_bound                    = true
BMW_numeric_offset33b_ready                       = true
BODY0_to_outer_vehicle_root_numeric_matrix_ready  = true
```

## Deliberate remaining boundary

This phase does **not** prove that the outer retail Vehicle root is the canonical
VHF hierarchy vehicle root. It consequently keeps:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready                   = false
vehicle_world_transform_ready                  = false
```

No static VHF matrix is multiplied into the physics bind here and no C++ runtime
ABI is changed. The artifact is the exact Process 1 -> Process 2 handoff required
by the next frame-composition proof.

It also records all of these negative claims explicitly:

- the native policy is not a retail live-session observation;
- no retail drift-mode default is inferred;
- no retail difficulty default is inferred to justify the selection;
- the selector-family arithmetic is not rederived;
- outer Vehicle/VHF identity is not assumed;
- the original game is not executed and no runtime capture is required.

## Reproduce

```bash
python3 tools/bind_bmw_offset33b_native_session_selector.py \
  evidence/bmw_offset33b_selector_complete_numeric.json \
  --physics-mode normal \
  --player-difficulty 1 \
  --session-target Silverstone+BMW_M3_E36 \
  --json-out evidence/bmw_offset33b_native_silverstone_session.json
```

The regression suite rebuilds the committed artifact byte-for-data-structure and
also checks all six selector pairs, duplicate rows, invalid domains, matrix/
translation disagreement, and an upstream contract that tries to preclaim a
singular numeric gate.

## Next blocker

The numeric BMW part of the BODY0 bind is no longer ambiguous for the target
native session. The remaining transform-semantic blocker is now exactly:

```text
outer Vehicle root
    ->
canonical BMW VHF vehicle-root / assembly frame
```

The existing #1241/#1242/#1245/#1248/#1253/#1263 static frontier should be
continued from its concrete chassis owner/storage results; broad renderer or SDF
owner searches should not be reopened.
