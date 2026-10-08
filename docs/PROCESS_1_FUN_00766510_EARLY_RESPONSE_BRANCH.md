# Process 1 — `FUN_00766510` early response branch ownership

## BLOCKER

P1.1 still requires the source/owner/order of the earlier `FUN_00766510` branch rooted at `HDVehicle+0x3b20`. Process 2 cannot remove the `contact_response` boundary while this branch is treated as an opaque callback side effect.

## INPUT

PC retail 1.02 `SHIFT.exe.c`, SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`, is authoritative. Xbox recompilation is not required for this promotion.

## OUTPUT

`SHIFT.Fun00766510EarlyResponseBranchOwnership/1` proves the following PC path:

- `HDVehicle+0x3b00` is setup-owned from `VehicleLoadData+0xcc8` and clamps two averaged runtime values before the response branch;
- `HDVehicle+0x3b08/+0x3b10/+0x3b18` is a setup-transformed application vector produced by `FUN_00753590` from `VehicleLoadData+0xcd0`;
- `HDVehicle+0x3b20..+0x3ba8` is a six-entry vector table with `0x18`-byte entries, populated by `FUN_00756bb0` from six `0x48`-byte setup records whose three evaluated source components begin at `VehicleLoadData+0xd08` and repeat at `+0x00/+0x14/+0x28` inside each record;
- the sixth table entry's Z lane, `HDVehicle+0x3ba8`, is **not** immutable setup data: `FUN_00766510` overwrites it immediately before calling `FUN_007551e0`;
- that runtime value depends on persistent `HDVehicle+0x3ae8`, setup-owned `+0x3af0/+0x3af8`, and the two clamped runtime values;
- `HDVehicle+0x3ae8` is itself persistent derived state written by `FUN_00756b60`, not a setup constant.

The source-visible runtime order is:

```text
clamp pair with +0x3b00
-> refresh +0x3ba8
-> FUN_007551e0(+0x3b20 table, current relative state)
-> transform +0x3b08 application vector
-> FUN_007baa70 BODY apply
-> FUN_00753650 caller-accumulator delta
-> +0x40a0/+0x40a8/+0x40b0 accumulation
```

## CONSUMER

Process 2 can internalize this branch using setup-owned table/application data plus persistent `+0x3ae8` and same-pass `+0x3ba8` refresh semantics. The whole `+0x3b20` table must not be frozen as a setup constant.

## GATES_CHANGED

- early `+0x3b20` branch ownership/order: **closed**;
- setup owner for `+0x3b00`, `+0x3b08`, and the six-vector table: **closed**;
- `+0x3ae8/+0x3ba8` immutable-setup claim: **false**;
- complete `FUN_00766510/contact_response` internalization: **still false**;
- top-level external-provider count remains **7**.

## LIMITS

No undocumented physical names are assigned. Selected BMW numeric values are not invented. The optional `+0x3bc8/+0x3cxx` branch remains P1.1 work.

## TESTS

`tests/test_process1_fun_00766510_early_response_branch.py` pins the PC source hash, setup offsets, mutable-lane conclusion, recompute call surface, and runtime ordering anchors.

## NEXT_OWNER

Process 2 may consume this contract. Process 1 continues P1.1 with the optional `+0x3bc8/+0x3cxx` branch and residual state/diagnostic writes.
