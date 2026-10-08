# Process 1 — `FUN_00765c40` callee classification join

## BLOCKER

After the direct write inventory and `FUN_00752fa0` proof, P1.2b still listed five potentially mutating callees. Four can now be removed from the unresolved set without inventing new physical semantics.

## INPUT

PC-retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`, plus the already-positive Phase 392 `FUN_007baa70` BODY accumulator contract.

## OUTPUT

`SHIFT.Fun00765c40CalleeClassificationJoin/1` classifies:

- `0x007aefb0` at caller sites `0x00765e0c` and `0x007663f6`: receiver-read-only 3x3-float transform; all writes land in an explicit qword vec3 output buffer;
- `0x007afd20` at `0x007660be`: receiver-read-only transform-plus-add helper; it calls `0x007aefb0` then adds another qword vec3 into the explicit destination buffer;
- `0x007b0430` at `0x007661e5`: receiver-read-only extractor; it converts `ecx+0x10/+0x14/+0x18` floats into the explicit fifth-argument qword vec3 output buffer;
- `0x007baa70` at `0x00766365` and `0x007664f2`: already-proven Phase 392 positive BODY accumulator primitive on `edi = [HDVehicle+0x33a0]`, updating `+0x48/+0x50/+0x58` and `+0x60/+0x68/+0x70` as `angular += r × v` and `linear += v`.

The first three are not receiver mutations. The fourth is a receiver mutation, but its complete side-effect surface is already positively owned.

## CONSUMER

Process 2 P2.4 can treat all four calls as classified. It should preserve explicit output-buffer dataflow for the first three and the Phase 392 BODY accumulator update for `FUN_007baa70`.

## GATES_CHANGED

- `0x007aefb0`: **classified**;
- `0x007afd20`: **classified**;
- `0x007b0430`: **classified**;
- `0x007baa70`: **classified by join to Phase 392**;
- unresolved P1.2b callee frontier: **only `0x007584f0`**;
- P1.2b complete: **false**;
- complete `FUN_00765c40` provider removal authorized: **false**;
- external-provider count: **7**.

## LIMITS

Output-buffer mutation is not silently equated with receiver mutation. This join does not classify `0x007584f0`, and it does not infer new force/torque units or gameplay field names beyond the existing Phase 392 algebraic accumulator contract.

## TESTS

`tests/test_process1_fun_00765c40_callee_classification_join.py` pins caller sites, receiver-mutation classification, the Phase 392 accumulator offsets/arithmetic, and the one-callee residual frontier.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Audit `0x007584f0` exhaustively. If its receiver and all nested side effects are positively classified, P1.2b can be adjudicated for completion; otherwise preserve the smallest explicit boundary that remains.
