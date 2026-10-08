# Process 1D — mode-2 camera target dependency frontier

## Result

The concrete mode-2 source is now proven and its target resolution path can be bounded without guessing a vehicle pointer.

PC retail 1.02 machine code establishes this chain:

```text
FUN_0080e1b0
  selected camera object
    -> FUN_0080e0d0
      -> mode-2 source vtable+0x90 = FUN_0081f7c0
        -> FUN_004b71f0(selected camera, 0x00c25fb8)
        -> source vtable+0x5c = FUN_006bbf70
        -> source+0x64 = RTTI-accepted selected camera object
```

`FUN_0081f2e0(source)` then resolves the active tracking target from `source+0x64`:

```text
source+0x64
  -> camera+0xe8
  -> nested+0xe8
  -> RTTI test 0x00c25fb8
  -> return nested target on success
  -> otherwise return source+0x64
```

This means the mode-2 source does not obtain a vehicle pointer directly from the activation argument. The next dependency is behind the TrackingCamera target/service path.

## Target acquisition surface

`FUN_0081f070` provides the bounded acquisition path already represented by `SHIFT.TrackingTargetLifecycleRuntime/1`:

- `FUN_00812aa0` / `FUN_0081ea70` prepare target state;
- `FUN_0080bfb0 -> FUN_0080b8e0` exposes the global camera service list;
- candidates are filtered by RTTI chain containing `0x00c25fb8`;
- candidate `+0x60` is compared with TrackingCamera `+0xd4` by `FUN_00408210`;
- the accepted candidate is stored by `FUN_00812970` at TrackingCamera `+0xe8`.

The exact machine body therefore supports a **tracking-target object dependency**, but it still does not prove that the accepted target object is the selected BMW/player vehicle.

## Pose/value surface

The camera pose path is narrower still:

- `FUN_0081f330` calls `FUN_008155f0` when the resolved target is usable;
- `FUN_008155f0` selects attached-target metadata or the CameraManager fallback;
- `FUN_00821080` consumes tracking target position values and copies them into camera position state before offset/orientation work;
- `FUN_00820a50 -> FUN_0081fbc0` uses the same resolved target path and camera service to initialize/update mode-2 state.

These are positive data-dependency facts. They are not yet an identity join to the project's proven `HDVehicle`/BODY0 world-pose chain.

## Adjudication

```text
mode2 runtime argument == selected player vehicle     REJECTED
mode2 concrete source/vtable                          PROVEN
mode2 depends on TrackingCamera target/service state  PROVEN
TrackingCamera target == selected BMW/player vehicle  UNPROVEN
TrackingCamera target pose == BODY0 world pose        UNPROVEN
retail vehicle-update -> camera-update ordering       UNPROVEN
native camera-follow admission                        BLOCKED
```

## Next exact join

Trace the producer/identity of the object accepted by `FUN_0081f070` / stored at TrackingCamera `+0xe8`, then join its transform/position producer to the already-proven selected retail vehicle/BODY0 identity. Only after that identity is exact should Process 1D close Phase 651 request 3 and proceed to scheduler ordering.
