# Process 1D — TrackingCamera target-field semantics

## Result

The previously modeled `FUN_00812aa0/FUN_0081f070` scan is **not** the player-vehicle target resolver.

PC-retail machine code and the `CTrackingCamData` reflection table separate two fields:

```text
CTrackingCamData +0x78 = Target
CTrackingCamData +0xd4 = OverridedBy
```

The `+0xd4` path compares a camera name against another TrackingCamera candidate and attaches that matched camera at runtime `+0xe8`. It is camera-to-camera override linkage and must not be promoted to selected-player/BMW target identity.

## Reflection proof

### Target

`FUN_008156b0` registers the literal `Target` at byte `+0x78`:

```text
0x00815892 push 0x00ac80ec   ; "Target"
0x008158a5 push 0x78
0x008158ab push 0x0d
0x008158b2 call FUN_0063a280
```

### OverridedBy

The same registration function maps `OverridedBy` to byte `+0xd4`:

```text
0x00815d69 push 0x00b15e2c   ; "OverridedBy"
0x00815d7c push 0xd4
0x00815d85 push 0x00
0x00815d8c call FUN_0063a280
```

## Runtime override resolution

`FUN_0081f070` scans service candidates and first requires the RTTI marker `0x00c25fb8`:

```text
0x0081f0f0 cmp eax,0xc25fb8
```

For a matching candidate it compares:

```text
candidate byte +0x60
against
current TrackingCamera byte +0xd4
```

with exact instructions:

```text
0x0081f10d lea ecx,[esi+0x60]
0x0081f110 add edx,0xd4
0x0081f116 call FUN_00408210
```

`FUN_00408210` is a null-terminated byte-string equality helper; its machine body loads and compares bytes from the two input strings. On a match `FUN_0081f070` calls `FUN_00812970`, which attaches the matched candidate at runtime camera byte `+0xe8`.

`FUN_00812aa0` contains the same `+0x60` versus `+0xd4` comparison pattern before `FUN_00812970`.

## Candidate type

The same RTTI marker `0x00c25fb8` participates in the TrackingCamera factory path:

```text
0x00823a2d cmp ecx,0xc25fb8
0x00823a35 push 0x150
...
0x00823a55 call FUN_0081f990
```

`FUN_0081f990` constructs/copies the TrackingCamera-sized object and installs its vtable. This independently supports the interpretation that `FUN_0081f070` links one camera to another, rather than resolving a manager vehicle entry.

## P1.4 impact

The already proven world-pose path remains unchanged:

```text
manager entry +0xfc numeric vehicle index
 -> FUN_00481420
 -> FUN_0070dcc0
 -> DAT_00c10b20[index]
 -> active render snapshot affine
 -> FUN_004394a0(target-local vector)
```

Only the semantic target-selection frontier changes.

```text
+0xd4 == player/BMW target                       REJECTED
+0xd4 == OverridedBy camera linkage              PROVEN
+0x78 == reflected CTrackingCamData Target        PROVEN
+0x78 -> selected player/BMW manager entry        OPEN
native camera-follow admission                    BLOCKED
external provider count                           7
```

## Next exact proof

Trace `CTrackingCamData Target` at byte `+0x78` through `FUN_008140c0`, `FUN_00814180`, and `FUN_00814210`, then through the target service at `CameraManager+0x574`. The required join is the exact value-flow from that target representation to the selected player/BMW `manager+0x2a0` entry. Do not reuse `FUN_0081f070` as target evidence.
