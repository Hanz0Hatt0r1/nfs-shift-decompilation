# Phase 739 — selected BMW FUN_00765c40 world-position join

Phase 738 closed every selected-session input to the Phase 728 `FUN_007618f0` local-sample producer. Phase 739 composes that producer with the already-native Phase 727 BODY0 transform at the exact per-pass persistent BODY observation point.

## Composition

For the selected Silverstone + BMW M3 E36 session the runtime now executes:

```text
current persistent BODY3/BODY4 origins
+ exact selected VehicleLoadData +0x338/+0x918 inputs
    -> Phase 728 FUN_007618f0 local sample (HDVehicle+0x3938)
    -> Phase 727 current BODY0 basis/origin transform
    -> Fun00765c40QueryInputBoundary.world_position
```

No renderer/VHF transform is used in this chain.

The new header is:

```text
native_runtime/include/shift_fun_00765c40_selected_bmw_world_position.hpp
```

with contract:

```text
SHIFT.Fun00765c40SelectedBMWWorldPosition/1
```

It reuses, rather than rederives, the Phase737, Phase738, Phase728 and Phase727 contracts.

## Exact pass timing

The existing `FUN_00770e80` composed anchor chain already publishes `current_body_observer` immediately before every pass anchor sequence. That observer reads the same authoritative persistent BODY vector later consumed by the half-step chain.

Therefore:

- pass 0 observes the current outer-step BODY state;
- pass 0 then executes its anchors and first `FUN_00765470` half-step;
- pass 1 observer sees the persistent BODY bytes produced by that first half-step;
- pass 1 cannot silently reuse the outer-step snapshot.

Phase739 propagates an optional current-BODY observer through the motion-read and contact-outer provider layers, composing it with the already-existing BODY0 motion/probe/+0x120 observer.

## Selected BMW domain gate

The source-backed BMW topology contains 11 BODY records at retail stride `0x170`. The new native join requires exactly that domain before replacing the external world position.

This matters because historical lower-chain fixtures intentionally use smaller synthetic BODY arrays. Those fixtures remain compatibility tests; they are not evidence for the selected BMW runtime. On a non-BMW synthetic domain, the session retains the fixture's explicit external world position instead of pretending the synthetic state is BMW data.

On the exact selected BMW domain, failure to compose the native world position fails closed.

## External boundary after Phase739

`NativeVehicleFun00765c40Provider` still exists and still executes once per pass. However, for the selected BMW domain its supplied `query_input.world_position` is no longer authoritative. The session overwrites that field with the native composition before validating/capturing the pass result.

The remaining external pass owns:

- the four `Fun00765c40LoadTerms`;
- query cache handle;
- `+0x38e8` miss fallback;
- collision-provider behavior below the typed query record;
- any residual source-backed-but-not-yet-internalized `FUN_00765c40` side effects.

The top-level provider count therefore remains seven. Phase739 narrows the complete pass boundary but does not yet remove it.

## Regression

`fun_00765c40_selected_bmw_world_position_check.cpp` constructs the exact 11-record BMW domain with an identity BODY0 basis and verifies the full Phase737 -> Phase728 -> Phase727 composition. It then changes BODY0/BODY3/BODY4 and re-executes the same function, proving that the result follows the current persistent BODY state rather than a cached outer-step snapshot.

The regression also rejects a two-BODY synthetic domain as a selected-BMW input.

## Next blocker

The next bounded target is the remainder of `FUN_00765c40`: split load-term/cache/fallback/collision-side-effect ownership so the current complete pass provider can be narrowed further without assigning unsupported physical semantics to the collision provider.
