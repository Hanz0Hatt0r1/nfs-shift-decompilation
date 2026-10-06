# Process 2 — consume the native Silverstone BMW `offset33b` selection

## Playable-slice blocker removed

Process 1 provides two consecutive contracts:

```text
SHIFT.BMWOffset33bSelectorCompleteNumeric/1
    -> all six admitted retail selector combinations

SHIFT.BMWOffset33bNativeSessionSelection/1
    -> explicit first playable Linux slice policy
```

The second contract deliberately chooses the target native session:

```text
session target    = Silverstone + BMW_M3_E36
physics mode      = normal
Player Difficulty = 1
```

This is project-owned native vertical-slice policy. It is not an inference that
a captured retail Silverstone session used those values.

PR #1277 stopped at a JSON Process 1 -> Process 2 handoff and explicitly did not
change the C++ runtime ABI. Phase 711 is the native consumer of that handoff.

Native contract:

```text
SHIFT.NativeBMWOffset33bRaceModeSelector/1
```

Implementation:

```text
native_runtime/include/shift_bmw_offset33b_race_mode_selector.hpp
native_runtime/src/bmw_offset33b_race_mode_selector.cpp
```

## Generic fail-closed selector

The reusable selector shape is:

```cpp
BmwOffset33bRaceModeSelector {
    ready,
    use_drift_cgheight_scale,
    player_difficulty
}
```

`ready=false` is rejected and Player Difficulty outside the source-backed
reflected domain `0..2` is rejected. The fourth lane present in the
PhysicsTweaker Vec4 is not admitted as a Player Difficulty value.

The generic consumer evaluates the corrected Process 1 arithmetic:

```text
auxiliary_weighted_COM =
(0,
 0.204869838976052848885218827415359207...,
 0.004335260115606936416184971098265896...)

mass_ratio = 173 / 1287

target_CG =
(0,
 0.28 * selected_CGHeight_scale,
 -0.081)

offset33b = (auxiliary_weighted_COM - target_CG) * mass_ratio
BODY0_to_outer.translation = -offset33b
```

The admitted scale rows remain:

```text
normal difficulty 0/1   = 0.60
normal difficulty 2     = 0.75
drift difficulty 0/1/2 = 0.25
```

All six combinations reproduce the three exact matrices from
`SHIFT.BMWOffset33bSelectorCompleteNumeric/1`.

## Native Silverstone policy consumption

Phase 711 also exposes:

```cpp
native_silverstone_bmw_offset33b_selector()
select_native_silverstone_bmw_body0_outer_vehicle_bind()
```

These functions consume, rather than rediscover, the policy admitted by
`SHIFT.BMWOffset33bNativeSessionSelection/1`:

```text
ready                         = true
use_drift_cgheight_scale      = false
player_difficulty             = 1
```

The selected result is therefore:

```text
BODY0 -> outer Vehicle translation =
(0,
 -0.004956085581085581085581085581085581...,
 -0.011470862470862470862470862470862471...)
```

with D3D/SVWT row-vector matrix:

```text
[1 0 0 0]
[0 1 0 0]
[0 0 1 0]
[0 -0.00495608558108558... -0.0114708624708625... 1]
```

For the first playable native session, Process 2 may now treat the numeric
`BODY0-local -> outer Vehicle root` matrix as ready.

## Ownership boundary

This phase intentionally stops at:

```text
BODY0-local -> outer Vehicle root
```

It does **not** construct `ProvenBmwBody0BindFrame`. The independent remaining
Process 1 relation is still unresolved:

```text
outer Vehicle root -> VHF vehicle root / assembly frame
```

Therefore all of these remain false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = false
BODY0_bind_frame_proof_ready                  = false
vehicle_world_transform_ready                 = false
```

No outer-Vehicle/VHF identity is inferred from matching offsets or from the
native session policy.

## Regression

```bash
cmake -S native_runtime -B out/native-runtime -DBUILD_TESTING=ON
cmake --build out/native-runtime \
  --target shift_runtime_bmw_offset33b_race_mode_selector_check
ctest --test-dir out/native-runtime \
  -R shift_runtime_bmw_offset33b_race_mode_selector --output-on-failure
```

The check:

- covers all six admitted selector combinations and all three unique matrices;
- rejects `ready=false`;
- rejects Player Difficulty `3`;
- verifies the native Silverstone selector is exactly normal + difficulty `1`;
- verifies that the selected native matrix equals the corrected Process 1 row;
- keeps the outer-Vehicle/VHF and final world-transform gates closed.

## Next blocker

Selector/mass/VDF ambiguity is no longer a blocker for the first playable slice.
The transform-semantic blocker is now exactly:

```text
outer Vehicle root
    ->
canonical BMW VHF vehicle-root / assembly frame
```

Once that relation is proven, the existing Phase 704-707 persistent BODY0
world-transform path can consume the completed bind frame without another
selector or `offset33b` reconstruction phase.
