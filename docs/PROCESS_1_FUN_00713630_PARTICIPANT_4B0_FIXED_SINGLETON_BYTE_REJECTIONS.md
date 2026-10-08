# Process 1A — reject fixed-singleton `+0x4b0` byte writers

## BLOCKER

After the VehicleLoadData constructor rejection, 13 direct-displacement `+0x4b0` writer sites remained unjoined. Two belong to the same exact fixed singleton receiver.

## OUTPUT

The receiver chain is already machine-closed:

```text
FUN_00518de0
  -> EAX = 0x00be1680
FUN_004567a0
  -> ECX = EAX
  -> FUN_0051f8f0
FUN_0051f8f0
  -> preserves receiver in ESI
  -> FUN_0051f8e0
FUN_0051f8e0
  -> tail-dispatches unchanged ECX to FUN_0051f850 or FUN_0051f800
```

The two candidate stores are therefore on receiver `0x00be1680`:

```text
0x0051f81c  mov byte ptr [ESI+0x4b0], AL
0x0051f8d2  mov byte ptr [ESI+0x4b0], 0
```

The selected PhysicsParticipant is instead the separately allocated `0x2b90` object stored in manager record `[0]`. No offset-equality or byte-width argument is used: receiver identity alone rejects both candidates.

## GATES_CHANGED

- `0x0051f81c`: **rejected**;
- `0x0051f8d2`: **rejected**;
- fixed singleton receiver `0x00be1680`: **closed**;
- unresolved direct-displacement candidates: **11**;
- actual selected participant runtime producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` provider removal: **not authorized**;
- external provider count: **7**.

## NEXT_STEP

Continue exact receiver-provenance adjudication of the remaining 11 direct-displacement writer sites. Width mismatch is never sufficient by itself; every rejection must remain rooted in object identity.
