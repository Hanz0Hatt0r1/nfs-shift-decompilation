# Process 1 — `FUN_00765c40` direct machine write surface

## BLOCKER

P1.2b requires exhaustive classification of residual `FUN_00765c40` side effects before the complete selected-session callback can be removed.

## INPUT

The authoritative PC-retail 1.02 `SHIFT.exe` is SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Direct disassembly of `0x00765c40..0x0076650f` was used for this inventory.

## OUTPUT

`SHIFT.Fun00765c40DirectMachineWriteSurface/1` closes the **direct machine write** subset of P1.2b.

Already-typed writes remain `HDVehicle+0x38dc` and `+0x38e0`. Newly pinned direct write groups are:

- four qwords at `+0x0a70/+0x14f0/+0x1f70/+0x29f0`;
- four qword pairs at `+0x0ba0/+0x0ba8`, then stride `0x0a80` through `+0x2b20/+0x2b28`;
- 12 dword pointer/result slots `+0x35c8..+0x35f4`;
- 12 qword scalar slots `+0x35f8..+0x3650`;
- byte `+0x3660`;
- qwords `+0x3668` and `+0x3670`;
- dword `+0x3678`;
- dword `+0x407c`, which machine code resets and increments according to positivity of the four already-closed load terms `+0x0b38/+0x15b8/+0x2038/+0x2ab8`.

No semantic field names are invented for the previously unnamed offsets.

## CONSUMER

Process 2 P2.4 may rely on this direct-write inventory when preserving the selected-session pass order. It must not treat this as proof that callee-mediated mutation is absent.

## GATES_CHANGED

- P1.2a: **closed**;
- P1.2b direct machine writes: **closed**;
- P1.2b callee-mediated side effects: **open**;
- P1.2b complete: **false**;
- complete `FUN_00765c40` provider removal authorized: **false**;
- external-provider count: **7**.

## LIMITS

Direct x86 stores and loop-derived destinations are proven. Calls can mutate receivers or pointed state even when no direct store is visible in this body, so absence of another `[esi+offset]` store is not proof of global side-effect absence.

Representative unresolved potentially mutating callees include `0x00752fa0`, `0x007584f0`, `0x007aefb0`, `0x007afd20`, `0x007b0430`, and `0x007baa70`. Pure math/helper calls should be eliminated from this set only with positive evidence.

## TESTS

`tests/test_process1_fun_00765c40_direct_machine_write_surface.py` pins the retail hash, function range, all direct write groups, the `+0x407c` count relationship, and the fail-closed callee gate.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Classify each potentially mutating callee by receiver/pointer provenance and side-effect surface. Only after that classification can P1.2b—and therefore the complete `FUN_00765c40` removal gate—close.
