# Process 1D — current vehicle transform camera handoff

## BLOCKER

P1.4 camera semantics were complete after the selected-player TrackCam proof, but the canonical camera frontier still referenced the historical Phase705 boolean handoff where `current_retail_BODY0_bind_ready` and `current_retail_world_matrix_ready` were false.

That historical report is no longer the current production transform authority. `main` already contains the later production contract:

```text
SHIFT.BMWPersistentWorldTransformRuntimeWiring/1
```

with `ready=true` and `OUTPUT.vehicle_world_transform_ready=true`.

## INPUT

Camera-side positive contracts:

```text
SHIFT.CameraFollowSourceFrontier/1
SHIFT.CameraFollowP14PlayableTargetEntityValue/1
```

Production transform contract:

```text
SHIFT.BMWPersistentWorldTransformRuntimeWiring/1
```

The production wiring explicitly consumes:

```text
SHIFT.BMWBody0BindFrameProof/1
SHIFT.NativeBMWBody0BindFrameRuntimeAdmission/1
SHIFT.NativeRetailGlobalVehicleBodyOwnerIdentity/1
SHIFT.PersistentBMWVehicleWorldTransform/1
```

and publishes the current BMW transform after the native fixed step.

## OUTPUT

This slice adds:

```text
SHIFT.CameraFollowP14CurrentVehicleTransformHandoff/1
```

The handoff is positive only when all of the following remain true:

```text
camera selected-player target identity                 true
camera vehicle-pose dependency                         true
retail physics-before-camera ordering                  true
S4 production world-transform wiring format            exact
S4 production wiring ready                             true
BODY0 bind proof contract                              exact
BODY0 bind runtime admission contract                  exact
persistent BMW world transform contract                exact
selected BODY index                                    0
same-fixed-step commit/publication before Phase715     true
```

No host frame rate or historical Phase705 boolean is used as semantic evidence.

## CURRENT TRANSFORM JOIN

The production S4 order is:

```text
positive BBFP admission
-> native_state.fixed_step(intent)
-> resolve prepared BMW vehicle-child static SVWT bind
-> commit_retail_bmw_vehicle_world_transform(...)
-> publish_persistent_bmw_vehicle_world_transform_for_render(...)
-> Phase715 freshness-gated consumer
```

The camera-side retail proof independently establishes:

```text
selected player TrackCam target
-> FUN_0080be50 / FUN_0080e1b0
-> mode2 active target ID

physics scheduler
-> vehicle/physics work
-> camera callback
-> mode2 +0x60 / FUN_008216a0
```

Therefore Process 1D can hand Process 2 a current selected-player vehicle transform source without reviving the obsolete Phase705 false gate.

## GATES_CHANGED

```text
P1.4 selected-player target identity          complete
P1.4 vehicle-pose dependency                  complete
P1.4 retail update ordering                   complete
P1.4 current vehicle-transform handoff        complete
P1.4 retail camera-follow proof               complete
Process 2 camera-feed implementation          ready to consume
P3.5 camera semantics handoff                 ready
camera runtime feed implemented               false
external provider count                       7
```

## LIMITS

- This PR does not implement the Process 2 camera runtime feed.
- It does not claim that the historical Phase705 contract was retroactively positive.
- It does not infer retail scheduling from host loop frequency.
- It does not alter the external provider count.
- It does not generalize the shipped TrackCam player-target proof to every camera type.

## NEXT_OWNER

Process 2.

## NEXT_STEP

Consume `SHIFT.CameraFollowP14CurrentVehicleTransformHandoff/1` to wire the current persistent BMW world transform into the native camera feed while preserving the proven physics-before-camera order. Process 3 P3.5 may consume the resulting runtime camera feed after that implementation lands.
