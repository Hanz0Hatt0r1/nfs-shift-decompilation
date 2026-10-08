# Process 1D — camera target runtime bridge

## Result

Phase 651 request 3 no longer waits on the rejected hypothesis that a `FUN_00489ad0()+0x2a0` collection entry is the selected `HDVehicle+0x4330` owner.

Process 1B has closed that direct identity negatively. PC-retail camera target queries nevertheless have a narrower positive data path inside the same collection entry:

```text
CameraManager+0x574
  -> DAT_00bc185c+4 service interface
  -> FUN_0045d940(target_id, selector, ...)
  -> FUN_0054ed00(manager+0x2a0, target_id)
  -> collection entry
  -> FUN_00481420(entry, selector, ...)
  -> FUN_004810a0 -> FUN_004585e6 -> FUN_004810bf
  -> entry+0x1e80 attached runtime object
```

The attached object is constructed by `FUN_00481d46`: allocation is followed by `FUN_0046c050`, the result is stored at `entry+0x1e80`, then `FUN_0046d7b0` updates the object from entry state beginning at `entry+0x1e84`.

## Target-position reads

The recovered dispatcher `FUN_004810bf` proves direct target-position dependencies on the attached object for several selectors:

- selector 2 falls back to `entry+0x1e80 + {0x10,0x14,0x18}` when `FUN_0047f870` does not supply a value;
- selector 4 invokes `FUN_0047f810(entry+0x1e80, output)`;
- selector 5 copies `entry+0x1e80 + {0x1c,0x20,0x24}`.

This is enough to prove that retail camera target transform resolution depends on pose-like state owned by an object attached to each manager collection entry. It is **not** enough to identify that object as the selected retail `HDVehicle`, BODY0, or their current world transform.

## Adjudication

```text
manager+0x2a0 entry == HDVehicle+0x4330              REJECTED (Process 1B)
manager entry -> entry+0x1e80 runtime dependency     PROVEN
entry+0x1e80 constructor path                        PROVEN
camera target selectors consume +0x1e80 state        PROVEN
entry+0x1e80 == selected HDVehicle/BODY0              UNPROVEN
entry+0x1e80 pose == current BODY0 world pose         UNPROVEN
Phase 651 request 3                                   OPEN, NARROWED
```

No name, layout similarity, or native behavior is used as an identity proof.

## Next exact proof

Trace the producer inputs to `FUN_0046d7b0(entry+0x1e80, entry+0x1e84)` and all retail writers of the attached object's position/transform lanes. Join those producers to the independently proven selected `HDVehicle`/BODY0 current-pose chain, or reject that join. Request 4 scheduling remains independently closed and must not be reopened unless contradictory retail evidence appears.
