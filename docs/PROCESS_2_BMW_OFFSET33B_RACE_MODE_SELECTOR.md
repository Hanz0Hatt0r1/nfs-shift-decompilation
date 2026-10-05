# Process 2 — BMW `offset33b` race-mode selector consumption

## Playable-slice blocker reduced

Process 1 now provides a selector-complete first-bootstrap BMW bind family:

```text
SHIFT.BMWOffset33bSelectorCompleteNumeric/1
```

It proves all admissible combinations of:

```text
RaceModeInfo+0x0e  normal/drift CGHeight-scale selector
RaceModeInfo+0x6c  Player Difficulty (0-2)
```

and reduces six selector combinations to three exact
`BODY0-local -> outer Vehicle` translations.

Process 2 previously had no native ABI for consuming that family.  Phase 711
adds:

```text
SHIFT.NativeBMWOffset33bRaceModeSelector/1
```

implemented by:

```text
native_runtime/include/shift_bmw_offset33b_race_mode_selector.hpp
native_runtime/src/bmw_offset33b_race_mode_selector.cpp
```

## Fail-closed selector

The native selector is explicit:

```cpp
BmwOffset33bRaceModeSelector {
    ready,
    use_drift_cgheight_scale,
    player_difficulty
}
```

No profile or race-mode default is synthesized.  `ready=false` is rejected and
Player Difficulty outside the source-backed domain `0..2` is rejected.  In
particular the fourth lane present in the PhysicsTweaker Vec4 is not admitted as
a Player Difficulty value.

## Numeric selection

The implementation consumes the exact Process 1 arithmetic:

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

The admitted scales are:

```text
normal difficulty 0/1 = 0.60
normal difficulty 2   = 0.75
drift difficulty 0/1/2 = 0.25
```

The resulting three native row-vector translation matrices match
`SHIFT.BMWOffset33bSelectorCompleteNumeric/1`.

## Ownership boundary

This phase intentionally returns only:

```text
BODY0-local -> outer Vehicle root
```

It does **not** construct `ProvenBmwBody0BindFrame`, because the independent
Process 1 relation remains unresolved:

```text
outer Vehicle root -> VHF vehicle root / assembly frame
```

Therefore this phase does not claim:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready = true
BODY0_bind_frame_proof_ready = true
vehicle_world_transform_ready = true
```

## Regression

```bash
cmake -S native_runtime -B out/native-runtime -DBUILD_TESTING=ON
cmake --build out/native-runtime \
  --target shift_runtime_bmw_offset33b_race_mode_selector_check
ctest --test-dir out/native-runtime \
  -R shift_runtime_bmw_offset33b_race_mode_selector --output-on-failure
```

The check covers all six admitted selector combinations, verifies the three
unique translations, and rejects both an unbound selector and Player Difficulty
`3`.

## Next blocker

Two independent joins remain:

1. a native producer must supply the live/source-backed ChangeRaceMode selector
   pair to this API;
2. Process 1 must prove `outer Vehicle root -> VHF vehicle root`.

The selector family no longer needs to be recomputed or guessed by downstream
physics/render code.
