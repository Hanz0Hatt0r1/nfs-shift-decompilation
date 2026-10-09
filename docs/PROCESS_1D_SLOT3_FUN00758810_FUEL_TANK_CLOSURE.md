# Process 1D — `FUN_00758810` fuel-tank branch closure

This P1.3D slice closes the sibling exact-HDVehicle branch from `FUN_0076d100`:

```text
0x0076d193  FUN_0076d100 -> FUN_00758810
ECX/param_1 = HDVehicle
```

The proof uses the pinned PC retail Ghidra SQLite direct edge plus the exact `SHIFT.exe.c` export SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`.

## Object identity

Vehicle setup binds the pointer at `HDVehicle+0x280` by name:

```c
iVar3 = FUN_007b3da0(*(void **)((int)this + 0x339c),"fuel_tank");
*(int *)((int)this + 0x280) = iVar3;
```

The existing BMW resource contract independently contains distinct SDF BODY identities:

```text
body       index 0
fuel_tank  index 9
```

`HDVehicle+0x33a0` is independently proven as the selected chassis BODY0 pointer. Therefore `HDVehicle+0x280` and `HDVehicle+0x33a0` are pointer fields to different BODY objects; neither field address is the pointed-to BODY storage.

## `FUN_00758810` destination surface

The recovered function loads the fuel-tank pointer twice from `HDVehicle+0x280` and directly updates only:

```text
fuel_tank BODY +0x60
fuel_tank BODY +0x68
fuel_tank BODY +0x70
```

It also calls `FUN_007baaf0` with the separately proven chassis BODY0 pointer from `HDVehicle+0x33a0`, and passes `HDVehicle+0x268` as a source/subobject argument to another helper.

The function contains no literal `0x28b8`, and none of its proven persistent destinations is the selected slot3 byte range `HDVehicle+0x28b8..+0x28bf`.

## Reproduction

```bash
python3 tools/ghidra/analyze_p1d_slot3_fun00758810_source.py \
  /path/to/SHIFT.exe.c \
  /path/to/shift_ghidra.sqlite \
  evidence/bmw_offset33b_resource_inputs.json \
  evidence/fun_007682c0_body0_delta_destination.json \
  --output out/p1d_slot3_fun00758810_source_closure.json
```

The analyzer fails closed on source/SQLite identity drift, the exact call edge, named `fuel_tank` binding, resource BODY indices, or chassis BODY0 identity drift.

## Gate boundary

This promotes only:

```text
slot3_fun0076d100_to_fun00758810_exact_root_branch_complete = true
```

It does not close stored/escaped aliases, other deeper direct aliases, or indirect/callback carriers. Slot3 writer provenance remains false, P1.3D remains false, aggregate P1.3 remains false, and external provider count remains 7.
