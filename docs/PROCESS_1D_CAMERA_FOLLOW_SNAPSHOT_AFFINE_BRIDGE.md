# Process 1D — camera target snapshot affine bridge

## Result

Phase 651 request 3 now has an exact PC-retail vehicle-pose dependency without requiring the rejected pointer hypothesis `manager+0x2a0 entry == HDVehicle+0x4330`.

The target entry stores its manager collection index as a numeric vehicle index and the camera path uses that value to fetch the corresponding active retail vehicle render snapshot.

## Index provenance

`FUN_00d60660` selects one entry from `manager+0x2a0` with index `ESI`. At the successful transition:

```text
0x00d606d8 push ESI
0x00d606db call FUN_00485290
```

`FUN_00485290` receives that index as `param_1` and stores it:

```text
0x00485293 mov eax,[ebp+0x08]
0x004852a1 mov [esi+0x100],eax
```

The same successful setup calls `FUN_00484cb0`; its final state publication copies:

```text
entry+0xfc = entry+0x100
```

with the exact machine store at `0x00485224`. The already merged `SHIFT.OuterVehicleRenderSnapshotAffineBridge/1` independently identifies this field as the SMS participant numeric vehicle index.

## Camera consumption

`FUN_00481420` does not guess a vehicle pointer. It reads the same numeric index directly from the camera target entry:

```text
0x00481477 mov ecx,[edi+0xfc]
0x0048147d push 7
0x0048147f push ecx
0x00481480 lea  ecx,[ebp-0x8f0]
0x00481486 call FUN_0070dcc0
```

The stack-local object at `[ebp-0x8f0]` is the affine destination.

Inside `FUN_0070dcc0/FUN_0070dccf` the first argument is range-checked and used literally as:

```text
slot = DAT_00c10b20 + numeric_vehicle_index * 0x1fa0
```

`FUN_0070db00` selects:

```text
slot + 0xd70 + (slot[+0x1f50] & 1) * 0x8f0
```

and `FUN_00481e20` copies that active snapshot into the caller's stack-local affine.

## Target-vector application

`FUN_004810bf` supplies the camera target-local vector. `FUN_00481420` then applies the fetched snapshot affine:

```text
FUN_004394a0(stack_affine, target_vector)
target_vector += stack_affine.translation
```

So the earlier `entry+0x1e80` lanes are not promoted to a world pose. They are local target/offset state. The world-space vehicle dependency is the indexed active render snapshot fetched by `FUN_0070dcc0`.

`SHIFT.OuterVehicleRenderSnapshotAffineBridge/1` already proves that this slot/snapshot family is published from the corresponding outer Vehicle, including common-source orientation and translated root affine.

## Adjudication

```text
entry+0xfc == numeric vehicle index                      PROVEN
camera target -> DAT_00c10b20[index] slot               PROVEN
camera target -> active vehicle render snapshot affine   PROVEN
entry+0x1e80 == world pose                               REJECTED / NOT PROMOTED
TrackingCamera target_id == selected player/BMW entry    UNPROVEN
Phase 651 request 3 pose dependency                      COMPLETE
Phase 651 request 3 selected-vehicle identity            OPEN
native camera-follow admission                           BLOCKED
```

## Next exact proof

Do not reopen the affine/snapshot producer. Trace the exact producer of the playable mode-2 `TrackingCamera` target id and prove or reject that it selects the current player/BMW manager entry. That is now the only camera-side semantic identity blocker in request 3.
