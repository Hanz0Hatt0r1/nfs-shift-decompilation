# Process 1A / P1.3A — slot0/slot1 same-function topology machine closure

## Result

The authoritative PC retail `SHIFT.exe` plus pinned `shift_ghidra.sqlite` function boundaries were scanned for functions that contain **both** exact machine scalar uses `+0x400` and `+0xa80` in the same recovered function body.

Across **41,538** sized functions, the bounded surface contains exactly **10** candidates:

```text
FUN_00757318
FUN_00763570
FUN_00765850
FUN_00765aa0
FUN_00765c40
FUN_00769520
FUN_0076b130
FUN_0076df50
FUN_00770e80
Unwind@00a705ae
```

All ten are closed negative as hidden f64 producers for P1.3A slot0 `HDVehicle+0x938` / slot1 `HDVehicle+0x13b8`.

## Important machine cases

`FUN_00757318` derives the exact wheel receiver at `vehicle_root + 0x400 + index*0xa80`. Its apparent `0x007576b0 [wheel+0x938]` store is a **DWORD** to wheel-local `+0x938`, which normalizes to slot0 absolute `HDVehicle+0xd38`, not `HDVehicle+0x938`. The called `FUN_007a25d0` does contain a DWORD `+0x538` store, but that receiver is loaded from the configuration table `[EBX+index*4+0x490]`, not the wheel receiver. The only callee that receives the exact wheel base, `FUN_00752fc0`, writes `+0x5b8/+0x7d8`.

`FUN_00763570` iterates `vehicle_root+0x400` in `0xa80` steps and forwards each wheel to `FUN_00755f80`. That helper mutates only the child object reached through `[wheel+0x420]`, at child offsets `+0x48/+0x50/+0x58`.

`FUN_00765850` and `FUN_00765aa0` directly update wheel-local `+0x505`, `+0x510`, `+0x518`, and `+0x520`; their remaining callees operate on the vehicle root, stack locals, or child/service pointers.

`FUN_00765c40` is already covered by `SHIFT.Fun00765c40DirectMachineWriteSurface/1`: its direct writes and callee-mediated side effects are exhaustive and contain no target slot producer.

The lifecycle candidates `FUN_0076b130`, `FUN_00769520`, and `Unwind@00a705ae` are vector constructor/destructor paths for four `0xa80` wheel elements starting at `vehicle_root+0x400`. Element constructor `FUN_0076b060` initializes `+0x2d0/+0x2d8/+0x400/+0x408/+0x5e0/+0x850` (plus small byte/dword fields), not `+0x538`; element destructor `FUN_007694b0` tears down the vptr and subobjects without a target store.

`FUN_0076df50` forwards each wheel to `FUN_00a62690` and `FUN_00a62f60`. The first writes only small local fields through `+0x2c`; the second treats the wheel as source and writes a separately allocated record.

`FUN_00770e80` dispatches exact wheel receivers to `FUN_00755a60` and `FUN_00760b50`. The former writes only `+0x7b0/+0x7b8/+0x7c0/+0x7f8/+0x800/+0x850` plus `FUN_00752fc0`'s `+0x5b8/+0x7d8`. The latter writes `+0x368` and `+0x868/+0x888/+0x8b0`; its final writer receives child `[wheel+0x420]`, not the wheel base.

## Reproducibility

`tools/ghidra/inventory_p1a_slot01_same_function_topology.py` checks both pinned hashes, uses Ghidra SQLite function boundaries, disassembles the retail executable with `objdump`, and requires exact scalar-token matches so `0x400` cannot match `0x4000`.

The captured result is `SHIFT.P1A.P13ASlot01SameFunctionTopologyMachineInventory/1`; semantic adjudication is `SHIFT.P1A.P13ASlot01SameFunctionTopologyMachineClosure/1`.

## Gate

```text
same-function topology candidates = 10
rejected                          = 10
same-function subset complete     = true
target f64 producer found         = false
slot0 complete                    = false
slot1 complete                    = false
P1.3 complete                     = false
provider count                    = 7
```

## Remaining frontier

This closure deliberately does **not** claim full alias exhaustion. P1.3A still must close:

- interprocedural aliases where wheel-base/stride derivation and the target write occur in different functions;
- overlapping bulk-copy or memory-initialization destinations that cover slot0/slot1 without carrying both topology constants in the same function.

No slot or provider gate may be promoted until those classes have exact selected-HDVehicle root provenance.