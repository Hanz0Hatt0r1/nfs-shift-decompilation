# Process 1D — active TrackingCamera target-ID producer

## Result

The active TrackingCamera runtime target-ID write site is now exact.

`FUN_0080e1b0` receives three independent values:

```text
param_1 = target manager-entry ID
param_2 = LookAt manager-entry ID
param_3 = camera object/config ID
```

On the mode-2 TrackingCamera path it publishes `param_1` into both the camera lane's current-target field and the active camera data object.

## Mode-2 activation flow

After resolving the selected camera object and identifying it as TrackingCamera, `FUN_0080e1b0` executes:

```text
FUN_0080e0d0(this, tracking_camera, param_3)
FUN_0080d500(this, param_1)
...
FUN_0080ce80(mode2_source, param_1)
FUN_0080cea0(mode2_source, param_2)
```

`FUN_0080d500` stores the current target ID at camera-lane `+0x26a4`.

`FUN_0080ce80` is the exact active-data setter:

```text
active_data = FUN_00812ed0(mode2_source)
if active_data != 0:
    active_data+0x74 = param_1
```

`FUN_0080cea0` performs the matching LookAt publication:

```text
active_data = FUN_00812ed0(mode2_source)
if active_data != 0:
    active_data+0x7c = param_2
```

The mode-2 write occurs only when `FUN_0081f2e0(mode2_source)[+0x68] == 1`, preserving the retail activation guard.

## Steady-state reuse

`FUN_00812050` proves that the lane's current target ID is later reused verbatim:

```text
local_18 = camera_lane+0x26a4
...
FUN_0080e1b0(camera_lane, local_18, local_18, camera_object_id)
```

Therefore `+0x26a4` and active camera data `+0x74` are not separate inferred identities: on this path the same numeric target ID is explicitly republished.

## What remains open

This closes the write-site/producer question but not the selected-player source question.

Known activation callers include `FUN_004b9350`, `FUN_004b94f0`, `FUN_0080be50`, `FUN_0080e650`, `FUN_00812050`, the `FUN_0050a*` camera/event path, and `thunk_FUN_00d91f10`.

The remaining semantic join is upstream:

```text
initial/retarget activation param_1
    -> FUN_0080e1b0
    -> lane+0x26a4
    -> active TrackingCamera data+0x74
    -> FUN_0045d940
    -> manager+0x2a0[param_1]
```

It is still necessary to prove that the playable initial/retarget `param_1` comes from `FUN_00459b80("player"/"teammate")` or another independently proven selected-player manager-ID source.

## Adjudication

```text
active camera data +0x74 write site                    PROVEN
+0x74 value == FUN_0080e1b0 param_1                    PROVEN
camera lane +0x26a4 tracks same target ID              PROVEN
steady-state path republishes +0x26a4 unchanged        PROVEN
initial activation param_1 == selected player ID       OPEN
selected player/BMW camera target identity             OPEN
native camera-follow admission                         BLOCKED
external provider count                                7
```

## Next exact proof

Trace the initial/retarget callers of `FUN_0080e1b0` and `FUN_0080be50`. Identify the exact value producer for argument 1 and prove or reject its equality with the selected-player ID returned by `FUN_00459b80("player"/"teammate")` or another already-proven player-ID source.
