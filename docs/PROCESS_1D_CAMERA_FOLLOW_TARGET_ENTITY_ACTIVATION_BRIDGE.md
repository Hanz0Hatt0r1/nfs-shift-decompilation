# Process 1D — target-entity activation bridge

## Result

The retail camera-event path now gives an exact string-to-runtime-target chain.

The 0x30-byte event record constructed by `FUN_0050a030` reflects `+0x20` as **`target entity`**. `FUN_0050a9c0` sends that exact string to the CameraManager target service's `+0x2c` resolver and then forwards the returned numeric manager-entry ID as `FUN_0080e1b0` argument 1.

Combined with `SHIFT.CameraFollowP14ActiveTargetIdProducer/1`, this proves:

```text
event target entity string
  -> FUN_00459b80
  -> numeric target manager-entry ID
  -> FUN_0080e1b0 param_1
  -> camera lane +0x26a4
  -> active TrackingCamera data +0x74
```

## Reflected event fields

`thunk_FUN_00d8cc00` registers the event record fields. For the target field, PC-retail machine code is:

```text
0x00d8cd55 push 0x00ac563c   ; "target entity"
...
0x00d8cd79 push 0x20         ; field offset
...
0x00d8cd86 call FUN_0063a280
```

The surrounding reflected fields are:

```text
+0x10  camera name
+0x18  event name
+0x20  target entity
+0x24  target location index
+0x2c  duration
```

`FUN_0050a030` constructs the string at `+0x20`, but does not write a retail literal `player` or `teammate` default into it. Therefore field meaning is proven while the playable value remains open.

## Target-name resolution

In `FUN_0050a9c0`, after selecting the current event record, exact machine flow is:

```text
0x0050ad05 call FUN_0080bfb0
0x0050ad0a cmp  [eax+0x574],0
0x0050ad18 mov  ecx,[eax+0x574]
0x0050ad21 mov  eax,[ecx]
0x0050ad23 mov  eax,[eax+0x2c]
0x0050ad26 add  edx,0x20
0x0050ad29 push edx
0x0050ad2a call eax
0x0050ad2c mov  ebx,eax
```

The merged target-service contract resolves `CameraManager+0x574` vtable `+0x2c` to `FUN_00459b80`. Thus `EBX` is exactly:

```text
FUN_00459b80(event_record.target_entity)
```

## Publication into TrackingCamera

When the event chooses an ordinary resolved camera and target ID is valid, the same `EBX` is passed twice to `FUN_0080e1b0`:

```text
0x0050ade7 push camera_object_id
0x0050ade8 push ebx            ; LookAt ID
0x0050ade9 push ebx            ; target ID / param_1
...
0x0050adf9 call FUN_0080e1b0
```

The alternate admitted branch repeats the same argument pair at `0x0050ae00..0x0050ae13`. Later camera-resolution paths repeat the same relation at `0x0050aeaa..0x0050aebd` and `0x0050aec4..0x0050aed7`.

`SHIFT.CameraFollowP14ActiveTargetIdProducer/1` then proves `FUN_0080e1b0 param_1 -> active camera data +0x74`.

## Remaining blocker

The service contract already proves that literal `player` or `teammate` passed to `FUN_00459b80` resolves through the current Participants Manager player slot to its numeric manager-entry ID.

What is still not proven is the concrete value stored in the **playable** event record `target entity` field. The event constructor initializes the string container only; it does not establish `player` as the default.

Therefore the remaining camera-side semantic join is now only:

```text
playable event target_entity value == "player" or "teammate"
```

or another exact value/source independently proven to select the current player/BMW manager entry.

## Adjudication

```text
event +0x20 field == "target entity"                         PROVEN
target entity -> FUN_00459b80                               PROVEN
resolver result -> FUN_0080e1b0 param_1                     PROVEN
target entity string -> active TrackingCamera +0x74         PROVEN
playable target entity value == player/teammate             OPEN
selected-player camera target identity                      OPEN
native camera-follow admission                              BLOCKED
external provider count                                     7
```
