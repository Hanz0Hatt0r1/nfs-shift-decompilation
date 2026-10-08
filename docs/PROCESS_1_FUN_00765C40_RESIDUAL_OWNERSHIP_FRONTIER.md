# Process 1 — `FUN_00765c40` ownership handoff

## BLOCKER

P1.2 was the Process 1 proof gate for Process 2 P2.4. It is now complete.

## Closed surface

The complete selected-session proof surface is now positively owned:

```text
selected per-pass world position       CLOSED
persistent +0x38dc cache lifetime      CLOSED
selected +0x38e8 miss fallback         CLOSED
typed FUN_007b0710 query/output seam   CLOSED
four wheel +0x738 load terms           CLOSED
FUN_0074f560 provider pointer domain   CLOSED: global 0x00c133ac
scene-query virtual dispatch           CLOSED: vtable slot +0x1c0
0x58-byte surface-record provenance    CLOSED
direct FUN_00765c40 write surface      CLOSED
callee-mediated object side effects    CLOSED
```

The lower collision implementation remains external by design. Process 2 must preserve `0x00c133ac` / vtable slot `+0x1c0` as a typed scene-query boundary until that lower implementation is independently replaced.

## Final P1.2b closure

The last unresolved callee was `FUN_007584f0` (`0x007584f0..0x00758802`). The retail machine span is 787 bytes with SHA-256 `252bade571ca266a620628da463c4cd3b3ca81333df0746d438cd95f77e2295f`.

It is called at `0x00765f2b` with `ecx = HDVehicle`. Its persistent object-state writes are exactly:

- qword `HDVehicle+0xd40`;
- qword `HDVehicle+0x17c0`;
- float `HDVehicle+0x3420`.

The first two are the two loop destinations of `[HDVehicle + index*0xa80 + 0xd40]` for indices 0 and 1. The final float stores the result of scalar helper `0x00783a30`.

All nested calls are classified. Vector transform/add/scale/cross helpers write stack-local or explicit output buffers; `0x007aefb0` is already classified as receiver-read-only; `0x00900b10`/`0x00900c40` are x87 cosine/sine wrappers that receive no HDVehicle/BODY pointer; `0x00783a30` is a scalar interpolation helper. No additional persistent game-object write is reachable through those calls.

No physical field names are assigned to `+0xd40`, `+0x17c0`, or `+0x3420`.

## CONSUMER

Process 2 P2.4 now has a complete Process 1 handoff. It may internalize the residual `FUN_00765c40` pass in exact retail order while retaining the lower collision scene-query dispatch as an explicit typed external boundary.

## GATES_CHANGED

- P1.2a: **closed**;
- P1.2b: **closed**;
- P1.2 complete: **true**;
- `FUN_00765c40` provider removal authorized for Process 2: **true**;
- lower collision scene-query implementation internalized: **false**;
- external-provider count before Process 2 consumption: **7**.

The provider count is deliberately not reduced in this Process 1 proof PR. The count changes only when Process 2 actually lands the runtime removal/replacement.

## LIMITS

This is an ownership/proof handoff, not a native runtime replacement. The x87 math wrappers may touch process floating-point environment internally; this proof only establishes that no HDVehicle/BODY pointer is passed to them and no additional persistent game-object mutation is introduced by that path.

## TESTS

`tests/test_process1_fun_007584f0_machine_side_effect_proof.py` pins the retail machine span, caller receiver, three persistent destinations, nested helper classification and completed P1.2 gate. Existing frontier tests are updated to require an empty unresolved-callee set.

## NEXT_OWNER

Process 2 P2.4.

## NEXT_STEP

Consume the completed P1.2 handoff, preserve exact pass order and all proven state writes, keep the `0x00c133ac/+0x1c0` scene-query boundary explicit, and remove the top-level residual callback only in the native runtime change that consumes this proof.
