# Process 1D — camera target service -> manager+0x2a0 join

## Result

The remaining P1.4 vehicle-pose dependency now reaches an already-known P1.3 identity frontier exactly.

At startup/runtime wiring:

```text
0x0040d834  EAX = DAT_00bc185c
0x0040d83d  ESI = EAX + 4          (when non-null)
0x0040d844  call FUN_0080bfb0
0x0040d84b  [EAX+0x574] = ESI
```

`FUN_0080bfb0()` is the camera singleton root. Therefore:

```text
CameraManager+0x574 = DAT_00bc185c + 4
```

Existing Process 1 proof independently identifies a non-null `DAT_00bc185c` value as the player-vehicle render-manager instance constructed by `FUN_0045ef50`.

## Exact secondary interface

`FUN_0045ef50` installs:

```text
render_manager+0x0 = 0x00ab5644
render_manager+0x4 = 0x00ab55f0
render_manager+0x8 = 0x00ab55e4
```

Thus the camera `+0x574` service points at the embedded `+4` interface with vtable `0x00ab55f0`.

Retail `.rdata` resolves the camera-used slots:

```text
0x00ab55f0 + 0x08 -> FUN_0045d940
0x00ab55f0 + 0x1c -> FUN_0045da00
0x00ab55f0 + 0x28 -> FUN_00459af0
```

## Target-id transform path

`FUN_00812d20`, used by the camera transform helpers, calls service vtable `+0x08` for a non-sentinel target id. That resolves to `FUN_0045d940`.

`FUN_0045d940` performs:

```text
FUN_00489ad0() -> manager
check target_id < manager+0x2c4
receiver = manager+0x2a0
FUN_0054ed00(receiver, target_id) -> collection entry
FUN_00481420(entry, ...camera transform arguments...)
```

Therefore camera target-transform queries with an explicit target id are serviced by the exact `FUN_00489ad0()+0x2a0` collection.

## Target metadata path

`FUN_00812de0`, reached from `FUN_008155f0`, calls service vtable `+0x1c`. That resolves to `FUN_0045da00`.

`FUN_0045da00` performs the same manager/index lookup:

```text
FUN_00489ad0() -> manager
check target_id < manager+0x2c4
FUN_0054ed00(manager+0x2a0, target_id) -> collection entry
if entry != 0 and entry+0x104 != 0:
    return entry+0x110
else:
    return 0
```

The camera metadata helper then reads three floats from returned-record `+0x1c/+0x20/+0x24`.

## Cross-process consequence

P1.4 request 3 no longer has an unconstrained camera-side identity search. Its exact unresolved identity is the same manager collection entry already owned by P1.3:

```text
manager+0x2a0[target_id]
    ?= selected retail player/BMW vehicle owner
    ?-> selected HDVehicle/BODY0 pose
```

P1.3 already proves the selection relation involving this collection but keeps exact collection registration/entry identity open. P1.4 must not independently guess that identity.

## Gates

Positive:

- camera `+0x574` service root -> `DAT_00bc185c+4`: proven;
- secondary interface vtable `0x00ab55f0`: proven;
- camera target transform `+0x08 -> FUN_0045d940`: proven;
- camera target metadata `+0x1c -> FUN_0045da00`: proven;
- both explicit target-id paths -> `FUN_00489ad0()+0x2a0[target_id]`: proven.

Still open:

- exact `manager+0x2a0[target_id]` entry identity for the selected player/BMW;
- entry transform/position -> selected BODY0 world-pose join;
- retail vehicle-update -> camera-update ordering/freshness.

Native camera-follow remains blocked and the external provider count remains **7**.

## Next step

Consume Process 1B's exact `P1.3.manager2a0` registration/entry identity when it becomes positive. In parallel, P1.4 can trace scheduler ordering because the remaining source identity has now been reduced to that explicit cross-process contract.
