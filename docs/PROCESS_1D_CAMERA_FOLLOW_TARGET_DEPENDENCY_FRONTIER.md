# Process 1D — mode-2 camera vehicle-pose dependency frontier

## Result

The concrete mode-2 source and its active-camera resolution are now bounded far enough to reject a false vehicle path.

PC retail 1.02 proves:

```text
FUN_0080e1b0
  selected TrackingCamera object
    -> FUN_0080e0d0
      -> source vtable+0x90 = FUN_0081f7c0
        -> source vtable+0x5c = FUN_006bbf70
        -> source+0x64 = selected TrackingCamera object
```

The object selected through `source+0x64` is camera data, not a vehicle. RTTI symbol `DAT_00c25fb8` is the 0x150-byte TrackingCamera data-copy type created by `FUN_0081f990`.

## `+0xe8` is an override camera, not the player vehicle

`CTrackingCamera` inherits the recovered `CStaticCamera` property layout. The relevant inherited properties are:

```text
+0x60  Name
+0x78  Target
+0x80  LookAt
+0x84  TargetOffset
+0xd4  OverridedBy
```

The retail copy constructor `FUN_00813300` initializes `+0xd4` as a string-like field through `FUN_00533e70`, sets `+0xd8 = -1`, and copies `+0xe8` from the source object.

`FUN_0081f070` then performs the runtime override lookup:

```text
this+0xd4 (OverridedBy)
  -> scan camera-service candidates
  -> require RTTI chain DAT_00c25fb8 (TrackingCamera)
  -> compare candidate+0x60 (Name) with this+0xd4 via FUN_00408210
  -> FUN_00812970(candidate)
  -> this+0xe8 = candidate
```

Therefore a non-null `TrackingCamera+0xe8` is another RTTI-accepted TrackingCamera selected by the `OverridedBy` name relation. It is not the selected BMW/player vehicle.

`FUN_00812ed0` confirms the same role for mode-2 resolution: it returns `source+0x64` (the selected TrackingCamera) or, when present, that camera's `+0xe8` override. `FUN_0081f2e0` adds a guarded nested override check but remains inside the same TrackingCamera RTTI domain.

## Remaining pose path

The remaining camera-to-world dependency is the camera target/service path, not `+0xe8`.

Exact retail flow includes:

- `FUN_008155f0` resolves the active camera through `FUN_00812ed0`, reads active-camera `+0x7c`, and passes that value to `FUN_00812de0`;
- `FUN_00812de0` obtains `FUN_0080bfb0()+0x574`, calls service vtable `+0x1c` with that id, and copies three floats from the returned record `+0x1c/+0x20/+0x24`;
- `FUN_00821080` resolves the active TrackingCamera through `FUN_0081f2e0`, consumes its `+0x20/+0x24/+0x28` position state and later uses the camera target-related `+0x74/+0x78/+0x84` fields through `FUN_00814030` / related transform helpers.

The registered `CStaticCamera` property table fixes `Target` at `+0x78` and `TargetOffset` at `+0x84`, but this proof does not infer that the service id/record is the selected vehicle merely from adjacency or naming.

## Adjudication

```text
mode2 runtime argument == selected player vehicle          REJECTED
mode2 concrete source/vtable                               PROVEN
source+0x64 == selected TrackingCamera object              PROVEN
TrackingCamera+0xe8 == selected player vehicle             REJECTED
TrackingCamera+0xe8 == TrackingCamera override             PROVEN
camera Target/service transform dependency                 PROVEN BOUNDED FRONTIER
target service record == selected BMW/BODY0 pose           UNPROVEN
retail vehicle-update -> camera-update ordering            UNPROVEN
native camera-follow admission                             BLOCKED
```

## Next exact join

Resolve the identity and producer semantics of `FUN_0080bfb0()+0x574` target records used by `FUN_00812de0` / `FUN_00812d20`, and trace the active camera target id/value into that service. Join that record's transform/position producer to the already-proven selected retail `HDVehicle` / BODY0 identity. Only then may Phase 651 request 3 be closed.
