# Process 1 — `FUN_00765c40` direct machine write surface

## INPUT

The authoritative PC-retail 1.02 `SHIFT.exe` is SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`. Direct disassembly of `0x00765c40..0x0076650f` was used for this inventory.

## OUTPUT

`SHIFT.Fun00765c40DirectMachineWriteSurface/1` closes the direct machine-write subset of P1.2b.

Already-typed writes remain `HDVehicle+0x38dc` and `+0x38e0`. Pinned direct write groups are:

- four qwords at `+0x0a70/+0x14f0/+0x1f70/+0x29f0`;
- four qword pairs at `+0x0ba0/+0x0ba8`, then stride `0x0a80` through `+0x2b20/+0x2b28`;
- 12 dword pointer/result slots `+0x35c8..+0x35f4`;
- 12 qword scalar slots `+0x35f8..+0x3650`;
- byte `+0x3660`;
- qwords `+0x3668` and `+0x3670`;
- dword `+0x3678`;
- dword `+0x407c`, reset and incremented according to positivity of the four closed load terms `+0x0b38/+0x15b8/+0x2038/+0x2ab8`.

No semantic field names are invented for unnamed offsets.

## CALLEE AUDIT

The later Process 1 proofs complete the callee-mediated side-effect surface:

- `SHIFT.Fun00752fa0WheelStateMachineProof/1` closes the four-wheel `+0x9f8/+0xa00` setter;
- `SHIFT.Fun00765c40CalleeClassificationJoin/1` closes the output-only transform/extractor helpers and joins `FUN_007baa70` to the proven Phase 392 BODY accumulator primitive;
- `SHIFT.Fun007584f0MachineSideEffectProof/1` closes the final callee, including persistent writes `HDVehicle+0xd40`, `+0x17c0`, and `+0x3420`.

There are no remaining unclassified callees in the `FUN_00765c40` machine body.

## CONSUMER

Process 2 P2.4 may use the complete direct/callee side-effect inventory when internalizing the residual pass. The lower collision scene query remains an explicit typed external boundary at provider pointer `0x00c133ac`, vtable slot `+0x1c0`.

## GATES_CHANGED

- P1.2a: **closed**;
- P1.2b direct machine writes: **closed**;
- P1.2b callee-mediated side effects: **closed**;
- P1.2b complete: **true**;
- `FUN_00765c40` provider removal authorized for Process 2: **true**;
- external-provider count before Process 2 consumption: **7**.

## LIMITS

This is a proof handoff, not the native runtime removal itself. Provider count is not reduced until Process 2 consumes the handoff. The lower collision-provider implementation is not guessed or internalized here.

## TESTS

`tests/test_process1_fun_00765c40_direct_machine_write_surface.py` pins the direct write surface and completed callee audit. `tests/test_process1_fun_007584f0_machine_side_effect_proof.py` pins the final unresolved callee and completed P1.2 gate.

## NEXT_OWNER

Process 2 P2.4.

## NEXT_STEP

Consume the completed P1.2 handoff in the native runtime while preserving exact retail pass order and the explicit lower scene-query provider boundary.
