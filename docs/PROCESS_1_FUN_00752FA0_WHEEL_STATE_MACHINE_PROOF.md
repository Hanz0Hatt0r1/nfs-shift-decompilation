# Process 1 — `FUN_00752fa0` wheel-state machine proof

## BLOCKER

P1.2b still contained callee-mediated side effects that could not be treated as absent merely because `FUN_00765c40` had no direct `[esi+offset]` store at those destinations.

## INPUT

Authoritative PC-retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

At `0x00765ec1`, `FUN_00765c40` calls `0x00752fa0` once per wheel with receiver `HDVehicle+0x400 + index*0x0a80`, index `0..3`, and the qword value loaded from `HDVehicle+0x98`.

## OUTPUT

The callee body is only five meaningful instructions:

```text
0x00752fa3  mov eax,[ebp+0x8]
0x00752fa6  fld qword [ebp+0xc]
0x00752fa9  fstp qword [ecx+0xa00]
0x00752faf  mov dword [ecx+0x9f8],eax
0x00752fb6  ret 0xc
```

Therefore the four vehicle-relative write pairs are:

```text
wheel 0: +0x0df8 dword, +0x0e00 qword
wheel 1: +0x1878 dword, +0x1880 qword
wheel 2: +0x22f8 dword, +0x2300 qword
wheel 3: +0x2d78 dword, +0x2d80 qword
```

The dword receives the wheel index. The qword receives the caller value from `HDVehicle+0x98`. No higher-level semantic field name is claimed.

## CONSUMER

Process 2 P2.4 may preserve these stores as part of the four-wheel pass and no longer needs to model `0x00752fa0` as an unknown side-effect boundary.

## GATES_CHANGED

- `0x00752fa0` callee side-effect surface: **closed**;
- unresolved callee frontier: reduced by one;
- P1.2b complete: **false**;
- complete `FUN_00765c40` provider removal authorized: **false**;
- external-provider count: **7**.

## LIMITS

This proof names only machine-backed receiver layout, offsets, widths, and value provenance. It does not assign an unproven gameplay/physics meaning to `wheel+0x9f8` or `wheel+0xa00`.

## TESTS

`tests/test_process1_fun_00752fa0_wheel_state_machine_proof.py` pins the exact callee instructions, four receiver lanes, vehicle-relative offsets, and fail-closed P1.2b gate.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Continue with the remaining potentially mutating callees, beginning with `0x007584f0` and `0x007baa70`, while eliminating transform/math helpers only when their receiver and write behavior is positively proven.
