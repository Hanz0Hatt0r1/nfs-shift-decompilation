# Process 1D — playable camera target value -> selected player

## Result

The remaining P1.4 camera-side selected-target value is now proven for a shipped playable retail `CCameraEvent` path.

`IGPHASEACTIVATE.bff` contains `scripts/postracenis/default.xml`. Its `TrackCam` event declares both:

```text
Camera Anchor = Player
Target        = Player
```

The PC-retail event dispatcher does not infer these values. It forwards the loaded `CCameraEvent` payload into the race/camera service, whose `TrackCam` handler resolves the strings through the same CameraManager name-to-target-ID service already proven in `SHIFT.CameraFollowP14TargetIdServiceBridge/1`.

## Shipped resource

Archive:

```text
IGPHASEACTIVATE.bff
SHA-256 6b2875e2a1ff0fe6c30c8ef6999d1e301808dae028800755cf11d3ccd557caee
```

Entry:

```text
scripts/postracenis/default.xml
SHA-256 aeab2e475efc106ae2caf397985c5e4600c8788d9f626654fb6294969cf2a3c5
```

The retail event at XML lines 779..790 is:

```text
class       CCameraEvent
Name        Cinematic cam
Camera Type TrackCam
Camera Name <empty>
Camera Anchor Player
Target      Player
```

This is resource provenance, not a string guessed from code.

## CCameraEvent layout

`FUN_006f77a0` constructs the event with vtable `0x00b01420`. `FUN_006f7930` reflects the relevant fields:

```text
+0x14 Camera Type
+0x18 Camera Name
+0x1c Camera Anchor
+0x20 Camera Anchor Relative Track Position
+0x24 Camera Local Anchor
+0x28 Target
+0x2c Relative Track Position
+0x30 Local Target
+0x34 derived Camera Type enum
```

The constructor itself defaults both `Camera Anchor` and `Target` to `Player`, independently matching the shipped resource.

## Event dispatch

`CCameraEvent` vtable `+0x4c = FUN_006f7770`. With a valid derived type it passes `CCameraEvent+0x14` to `DAT_00c0f7f4` vtable slot `+0x128`.

The concrete service object is constructed by `FUN_004b7250` with vtable `0x00abec20`; that vtable's `+0x128` slot is exactly `FUN_004b9670`.

`FUN_004b9670` dispatches derived camera type `1` (`TrackCam`) to `FUN_004b9350`.

Because the handler receives `CCameraEvent+0x14` as its payload:

```text
payload+0x08 = CCameraEvent+0x1c Camera Anchor
payload+0x14 = CCameraEvent+0x28 Target
```

`FUN_004b9350` resolves both through vtable slot `+0x14`:

```text
0x004b9365 lea edx,[esi+0x08]  ; Camera Anchor string
...
0x004b9378 lea ecx,[esi+0x14]  ; Target string
```

The service `+0x14` slot is `FUN_004b6f20`, which calls its `+0x10` resolver. `+0x10 = FUN_004b72c0`, a direct trampoline to:

```text
CameraManager+0x574 vtable+0x2c
```

The previously proven concrete target is `FUN_00459b80`, where case-insensitive `player`/`teammate` resolves to:

```text
FUN_00489ad0()->+0x374->+0x100
```

Therefore the shipped `Player` value resolves to the current player manager-entry ID.

## Activation join

For the shipped `TrackCam` event the camera name is empty. `FUN_004b9350` takes the empty-name branch at `0x004b9456..0x004b9476` and passes the resolved anchor ID in both target-ID positions to `FUN_0080be50`:

```text
FUN_0080be50(CameraManager, player_id, player_id, FUN_00811a20(...), 0)
```

`FUN_0080be50` immediately forwards those arguments to `FUN_0080e1b0` when camera reception is active. Thus `FUN_0080e1b0 param_1` is the selected/current player manager ID on this shipped TrackCam path.

The named-camera branch independently passes the resolved anchor and Target IDs directly to `FUN_0080e1b0`; if Target resolution returns `-1`, Target falls back to the anchor ID.

Once `FUN_0080e1b0` selects a `TrackingCamera` object, the already-proven mode-2 path preserves this exact `param_1` through:

```text
FUN_0080d500 -> camera lane+0x26a4
FUN_0080ce80 -> active camera data+0x74
```

No numeric-ID equality is inferred: the value is followed from the shipped string through the exact resolver and activation call.

## Adjudication

```text
shipped playable TrackCam Camera Anchor == Player            PROVEN
shipped playable TrackCam Target == Player                   PROVEN
Player -> current player manager ID                          PROVEN
TrackCam activation param_1 == current player manager ID     PROVEN
mode-2 selected-player target identity on admitted transition PROVEN
Phase 651 request 3 selected-player identity                 COMPLETE
Phase 651 request 3                                           COMPLETE
native camera-follow admission                                STILL BLOCKED
external provider count                                       7
```

Native follow is deliberately not promoted here. The current-retail BODY0/world-matrix handoff and persistent-transform transport contracts remain independent required gates.
