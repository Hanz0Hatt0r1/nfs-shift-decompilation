# Process 1A — reject `FUN_00481e20` from the participant `+0x4b0` frontier

## BLOCKER

`FUN_00481e20` contains a literal field-by-field copy through `+0x4b0`, so its generic body cannot be rejected until every destination family is rooted.

## OUTPUT

The candidate operation is:

```text
0x00482a54  fld  dword ptr [EDI+0x4b0]
0x00482a5a  fstp dword ptr [ESI+0x4b0]
```

All direct destination families are already machine-backed by merged ownership contracts:

1. `0x0070db29`: the forwarded `FUN_0070dcc0 -> ... -> FUN_0070db00` surface is rooted to stack-local destination storage.
2. `0x004848f5`: destination is participant-owned render snapshot `parent+0xa00`, so the candidate store lands at parent `+0xeb0`, not selected participant `+0x4b0`.
3. `0x0081d335`: destination is `CCameraView+0x2d0` state.

No direct caller therefore passes the selected PhysicsParticipant root as `FUN_00481e20` destination.

This proof only reuses already-merged Process 1B/1D identity boundaries. It does not modify or reinterpret their control/camera semantics.

## GATES_CHANGED

- `FUN_00481e20 @ 0x00482a5a`: **rejected**;
- complete direct destination surface for this generic bulk copy: **closed**;
- unresolved direct-displacement candidates: **9**;
- selected participant runtime `+0x4b0` producer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` removal: **not authorized**;
- provider count: **7**.

## NEXT_STEP

Continue exact receiver-provenance adjudication of the remaining nine direct-displacement candidates. Generic copy functions remain rejected only when their complete destination surface is closed.
