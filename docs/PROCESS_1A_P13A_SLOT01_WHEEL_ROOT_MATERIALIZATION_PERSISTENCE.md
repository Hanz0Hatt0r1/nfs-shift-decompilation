# Process 1A / P1.3A — slot0/slot1 wheel-root materialization and persistence

## Scope

After direct exact-HDVehicle-root persistence closed, P1.3A still needs the derived wheel roots for selected slot0 `HDVehicle+0x938` and slot1 `HDVehicle+0x13b8` bounded before wider interior/runtime/callback alias work.

This handoff consumes two merged P1D machine contracts without changing their ownership:

- `SHIFT.P1D.Slot3SixteenCarrierDirectRootPersistence/1`;
- `SHIFT.P1D.Slot3MachineWheelRootMaterializationClosure/1`.

The first supplies direct exact-wheel-root store/push/GPR-copy persistence for the five wheel-root carriers. The second proves the two known `HDVehicle -> wheel root` materialization paths and exact four-wheel geometry.

## Exact slot geometry

The wheel roots are:

```text
slot0 = HDVehicle+0x400
slot1 = HDVehicle+0xe80
slot2 = HDVehicle+0x1900
slot3 = HDVehicle+0x2380
stride = 0xa80
```

The consumed field is wheel-local `+0x538..+0x53f`, therefore:

```text
slot0 target = HDVehicle+0x400+0x538 = HDVehicle+0x938..+0x93f
slot1 target = HDVehicle+0xe80 +0x538 = HDVehicle+0x13b8..+0x13bf
```

No numeric coincidence is used as object identity; the wheel roots come from machine-proven materialization from the exact HDVehicle receiver.

## Materialization paths

### `FUN_00763570`

The four-wheel loop seeds `HDVehicle+0x400`, stores the cursor only in stack local `[EBP-0x4]`, calls `FUN_00755f80` at `0x0076360f`, advances by `0xa80`, and runs exactly four iterations. No non-stack wheel-root store exists in the bounded loop.

### `FUN_00770e80`

Explicit materializations pass the exact roots to `FUN_00760b50`:

| slot | wheel root | materialization | consumer call |
| --- | --- | --- | --- |
| 0 | `HDVehicle+0x400` | `0x007710fe` | `0x00771107` |
| 1 | `HDVehicle+0xe80` | `0x0077111c` | `0x00771125` |

Across the bounded materialization window there are zero wheel-root pushes and zero non-stack wheel-root stores.

## Exact wheel-root carrier persistence

The five exact-wheel-root carriers are:

```text
FUN_00752fc0
FUN_00755950
FUN_00755a60
FUN_00755f80
FUN_00760b50
```

Within the merged direct-root machine surface:

```text
direct exact-wheel-root memory stores = 0
direct exact-wheel-root pushes        = 0
direct root-register copies           = 1
```

The only copy is `0x00755db3` in `FUN_00755a60`, `ECX=ESI`, an immediate receiver reload. No new persistent GPR alias class appears.

## Gate

```text
known slot0/slot1 wheel-root materialization subset complete = true
direct exact-wheel-root persistence subset complete         = true
non-stack exact-wheel-root store found                       = false
exact-wheel-root push found                                  = false
new persistent exact-wheel-root GPR alias found              = false

interior/child alias storage ruled out                       = false
reconstructed wheel pointers ruled out                       = false
runtime-generated/copied pointer stores ruled out            = false
callbacks / indirect entry ruled out                         = false
stored-or-escaped aliases ruled out                          = false
slot0 complete                                               = false
slot1 complete                                               = false
P1.3 complete                                                = false
provider count                                               = 7
```

## Reproduce

```bash
python3 tools/ghidra/build_p1a_slot01_wheel_root_materialization_persistence_handoff.py \
  --persistence evidence/p1d_slot3_16carrier_direct_root_persistence.json \
  --materialization evidence/p1d_slot3_machine_wheel_root_materialization_closure.json \
  --output evidence/p1a_p13a_slot01_wheel_root_materialization_persistence_handoff.json
```

The builder fails closed on source-format/hash drift, carrier-set drift, new direct wheel-root stores/pushes/copies, geometry drift, changed loop storage, or changed slot0/slot1 explicit consumer sites.

## Next step

Consume already-machine-bounded wheel interior/child alias tranches where the conclusions are slot-agnostic, then trace reconstructed/runtime-generated pointers and callback/indirect-entry carriers before changing the global stored-or-escaped-alias gate.
