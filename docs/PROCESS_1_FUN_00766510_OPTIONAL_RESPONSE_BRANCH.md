# Process 1 — `FUN_00766510` optional response branch ownership

## BLOCKER

P1.1 still contains the optional `HDVehicle+0x3bc8/+0x3cxx` branch. Until its setup and mutable-state owners are explicit, Process 2 cannot safely remove the top-level `contact_response` provider.

## INPUT

Authoritative source is PC retail 1.02 `SHIFT.exe.c`, SHA-256 `512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`. Xbox recompilation was not required for any promoted claim.

## OUTPUT

`SHIFT.Fun00766510OptionalResponseBranchOwnership/1` proves:

- `HDVehicle+0x3bc8` is the setup gate copied from `VehicleLoadData+0xf10`;
- the main coefficient block (`+0x3bd8/+0x3be0/+0x3be8/+0x3bf0/+0x3bf8/+0x3c00/+0x3c08/+0x3c10/+0x3c30`) is setup-owned from exact `VehicleLoadData` offsets;
- `+0x3c18/+0x3c20/+0x3c28/+0x3c38` is a setup-derived shape controlled by `VehicleLoadData+0xf78/+0xfa0`;
- `+0x3c40` is setup-configured helper state from `+0xfa8/+0xfb0/+0xfb8`;
- `+0x3c60/+0x3c68/+0x3c70` is a setup-transformed application vector sourced from `VehicleLoadData+0xfc0`;
- `HDVehicle+0x3bd0` is **not** a setup constant. It is initially evaluated from `VehicleLoadData+0xf14`, then mutated by `FUN_00757fa0`, clamped/reset by `FUN_00758170` and `FUN_00769d60`, and may be replaced by `FUN_0076ed60` state load.

The recovered runtime order is:

```text
+0x3bc8 gate and local_50 < 0
-> coefficient polynomial / clamps
-> FUN_00755340(+0x3c40)
-> require negative curve-scaled result
-> FUN_007af040 BODY scalar path
-> transform +0x3c60 application vector
-> FUN_007baa70 BODY apply
-> caller accumulator
-> optional +0x4298.. diagnostic writes
```

## CONSUMER

Process 2 can consume the setup-owned block while preserving `+0x3bd0` as persistent mutable state. Freezing the entire optional block as selected-BMW setup data would be incorrect.

## GATES_CHANGED

- optional branch setup owner: **closed**;
- optional branch runtime order: **closed**;
- `+0x3bd0` immutable setup claim: **false**;
- complete `FUN_00766510/contact_response` internalization: **still false**;
- active top-level provider count remains **7**.

## LIMITS

This slice does not claim physical names for the optional branch. It does not yet close every residual diagnostic/state write outside this branch or prove the full tail of `FUN_00766510` removable. Selected BMW numeric values are not synthesized.

## TESTS

`tests/test_process1_fun_00766510_optional_response_branch.py` pins the PC source hash, setup offsets, `+0x3bd0` mutation surface, runtime gating/order, and fail-closed non-removal conclusion.

## NEXT_OWNER

Process 2 may consume this contract. Process 1 should now audit the remaining `FUN_00766510` tail/state/diagnostic writes and decide whether P1.1 is complete enough for provider removal.
