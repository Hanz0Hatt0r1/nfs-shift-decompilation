# Process 1A / P1.3A — known slot0/slot1 interior and child alias handoff

## Scope

Merged P1A evidence now fixes slot0/slot1 exact wheel roots and their direct persistence. The next bounded alias layer contains three transformed receiver families that already have PC-retail machine closures in P1D:

1. `wheel+0x80 -> FUN_007555b0`;
2. `wheel+0x7c8 -> FUN_00753620`;
3. `child=[wheel+0x420]` and `child+0xd4` helper chains.

This handoff consumes only the slot-agnostic machine conclusions. P1D retains ownership of the upstream proofs; P1A slot identity comes from `SHIFT.P1A.P13ASlot01WheelRootMaterializationPersistenceHandoff/1`.

## Slot normalization

```text
slot0 wheel = HDVehicle+0x400
slot1 wheel = HDVehicle+0xe80
slot0 target = HDVehicle+0x938..+0x93f
slot1 target = HDVehicle+0x13b8..+0x13bf
```

For the two interior receivers:

```text
slot0 wheel+0x80  = HDVehicle+0x480
slot1 wheel+0x80  = HDVehicle+0xf00
slot0 wheel+0x7c8 = HDVehicle+0xbc8
slot1 wheel+0x7c8 = HDVehicle+0x1648
```

## `wheel+0x80`

The machine-proven `FUN_00758b50` per-wheel loop materializes `HDVehicle+0x400+slot*0xa80` and forwards it to `FUN_00755950`. That function reads wheel-local `+0x538`, does not write it, and its only direct callee receives `ECX=wheel+0x80`.

`FUN_007555b0` is completely bounded:

- target `wheel+0x538` would be callee-relative `+0x4b8`;
- observed receiver-relative memory offsets stop at `+0x260`;
- receiver-relative writes are only `+0x248/+0x250/+0x258/+0x260`, i.e. wheel-relative `+0x2c8/+0x2d0/+0x2d8/+0x2e0`;
- direct calls = 0;
- receiver reconstruction/mutation = 0.

Therefore the interior pointer neither writes slot0/slot1 `+0x538` nor reconstructs/forwards the exact wheel root.

## `wheel+0x7c8`

`FUN_00755a60` has exact receiver `HDVehicle+0x400+slot*0xa80`. At `0x00755c04` it derives `ECX=wheel+0x7c8` and forwards that unchanged at `0x00755dae` to `FUN_00753620`.

The bounded leaf has no direct calls and writes only receiver `+0x0`, therefore exactly wheel `+0x7c8`, disjoint from target wheel `+0x538`.

## `[wheel+0x420]` child chain

The exact slot0/slot1 wheel carriers `FUN_00760b50` and `FUN_00755f80` load a child pointer from `[wheel+0x420]`; transform calls may receive `child+0xd4`.

The bounded machine chain covers `FUN_007ba860`, `FUN_007ba7e0`, `FUN_007af0a0`, `FUN_007af010`, and `FUN_007aefb0`. It finds:

- no child-relative GPR pointer loads/stores that recover or persist a wheel/back pointer;
- no wheel-root reconstruction;
- no child-pointer persistence;
- `FUN_007ba860` persistent writes only to child scalar state `+0x128/+0x12c/+0x130/+0x138/+0x140/+0x148`;
- no selected wheel `+0x538` writer.

## Gate

```text
wheel+0x80 interior alias subset complete   = true
wheel+0x7c8 interior alias subset complete  = true
wheel+0x420 child alias subset complete     = true
known subset target writer found            = false
known subset wheel-root reconstruction      = false
known subset pointer persistence            = false

other derived/child aliases ruled out       = false
reconstructed wheel pointers ruled out      = false
runtime-generated/copied pointers ruled out = false
callbacks / indirect entry ruled out        = false
stored-or-escaped aliases ruled out         = false
slot0 complete                              = false
slot1 complete                              = false
P1.3 complete                               = false
provider count                              = 7
```

## Reproduce

```bash
python3 tools/ghidra/build_p1a_slot01_known_interior_child_alias_handoff.py \
  --output evidence/p1a_p13a_slot01_known_interior_child_alias_handoff.json
```

The builder validates all six merged contracts, retail SHA-256, exact slot identities, per-wheel forwarding, complete bounded callee write surfaces, no root reconstruction, and fail-closed upstream premises.

## Next step

Consume the remaining four-wheel interior aliases already machine-bounded in `FUN_00765c40` (`wheel+0x678`, `wheel+0x7a8`) where the conclusions are slot-agnostic. Then continue reconstructed/runtime-generated pointer stores and callback/indirect-entry carriers before changing the global stored-or-escaped-alias gate.
