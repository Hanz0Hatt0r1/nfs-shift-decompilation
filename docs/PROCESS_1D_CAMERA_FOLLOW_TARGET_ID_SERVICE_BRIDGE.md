# Process 1D — camera target-ID service bridge

## Result

The P1.4 selected-target frontier is narrower than the earlier `CTrackingCamData Target` field name suggested.

PC-retail machine code proves that the runtime camera data carries two separate values for target resolution:

```text
camera data +0x74 = hidden target manager-entry ID, default -1
camera data +0x78 = reflected Target selector/type, default 6
camera data +0x7c = hidden LookAt manager-entry ID, default -1
camera data +0x80 = reflected LookAt selector/type, default 6
```

The reflected `Target` field at `+0x78` is therefore **not** the numeric manager collection index.

## Constructor boundary

`FUN_00813180` initializes the four adjacent fields independently:

```text
+0x74 = 0xffffffff
+0x78 = 6
+0x7c = 0xffffffff
+0x80 = 6
```

The reflection registration independently names `+0x78` as `Target` and `+0x80` as `LookAt`.

## Camera target service

`FUN_0040d6a0` installs the service interface:

```text
CameraManager+0x574 = DAT_00bc185c + 4
```

The object is constructed by `FUN_0045ef50`; the `+4` interface uses vtable `0x00ab55f0`.

Relevant exact slots are:

```text
+0x08 = FUN_0045d940
+0x0c = FUN_0045d980
+0x14 = FUN_0045d9c0
+0x1c = FUN_0045da00
+0x2c = FUN_00459b80
```

## ID versus selector

`FUN_00812d20` invokes service slot `+0x08`. Exact `FUN_0045d940` machine flow proves the second argument is the manager lookup ID while the first argument is the selector:

```text
0x0045d943 call FUN_00489ad0
0x0045d948 mov edx,[ebp+0x0c]     ; target ID
0x0045d94b cmp edx,[eax+0x2c4]
0x0045d953 lea ecx,[eax+0x2a0]
0x0045d959 call FUN_0054ed00       ; manager+0x2a0[target ID]
...
0x0045d969 mov ecx,[ebp+0x08]      ; selector
0x0045d970 call FUN_00481420       ; resolved entry + selector
```

The active camera helpers source those arguments separately:

```text
Target: +0x74 ID, +0x78 selector
LookAt: +0x7c ID, +0x80 selector
```

## Player-name resolver

Service slot `+0x2c` is `FUN_00459b80`. It resolves symbolic vehicle names to numeric manager IDs.

Exact machine anchors include:

```text
0x00459ba8 push "player"
0x00459bae call __stricmp
...
0x00459bba call FUN_00489ad0
0x00459bbf mov eax,[eax+0x374]
0x00459bc9 mov eax,[eax+0x100]

0x00459be2 push "teammate"
0x00459be8 call __stricmp
```

For both `player` and `teammate`, this path returns the current participant/player manager ID through `manager+0x374 -> +0x100`.

Other accepted forms include numeric text, `last`, and a service fallback.

## Adjudication

```text
CTrackingCamData +0x78 == manager entry ID             REJECTED
CTrackingCamData +0x78 == Target selector              PROVEN
runtime camera data +0x74 == target lookup ID          PROVEN
runtime camera data +0x7c == LookAt lookup ID          PROVEN
service +0x08 -> manager+0x2a0[id]                     PROVEN
"player" -> current player manager ID                  PROVEN
active playable camera +0x74 <- "player" resolver      OPEN
selected player/BMW target identity                    OPEN
native camera-follow admission                         BLOCKED
external provider count                                7
```

The previously proven snapshot-affine path remains unchanged once an entry is selected.

## Next exact proof

Trace every producer of the active playable TrackingCamera data field `+0x74` (and `+0x7c` where relevant). The required positive join is a concrete write/copy/materialization path from `FUN_00459b80("player"/"teammate")`, or another independently proven selected-player numeric ID source, into the active runtime target-ID slot.

Do not infer the join merely because a camera resource says `Target=player` or because both values are numeric IDs.
