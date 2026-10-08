# Process 1A — reject `0x004dbf73` from the participant `+0x4b0` frontier

## BLOCKER

Ten-plus direct-displacement writer candidates still require exact base-object identity before the selected PhysicsParticipant `+0x4b0` producer can be closed.

## OUTPUT

`0x004dbf73` belongs to `FUN_004dbdb0`, whose direct call surface has exactly one caller. The caller allocates a separate `0x600`-byte object immediately before construction:

```text
0x00549c43  push 0x600
0x00549c48  call FUN_008868c0
0x00549c54  mov ECX,EAX
0x00549c56  call FUN_004dbdb0
0x00549c61  [caller+0x10] = EAX
```

`FUN_004dbdb0` captures this allocation as `ESI=ECX`, initializes several embedded regions, and later executes:

```text
0x004dbf73  fst dword ptr [ESI+0x4b0]
```

The selected PhysicsParticipant has an exact, separate `0x2b90` allocation root. The sole direct constructor root therefore proves this writer belongs to the `0x600` allocation, not to PhysicsParticipant.

## GATES_CHANGED

- direct candidate `0x004dbf73`: **rejected**;
- exact `0x600` constructor receiver identity: **closed**;
- unresolved direct-displacement candidates: **10**;
- actual selected participant runtime writer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` provider removal: **not authorized**;
- external provider count: **7**.

## NEXT_STEP

Continue exact receiver-provenance adjudication of the remaining 10 direct-displacement `+0x4b0` sites before widening to computed-address, escaped-alias, indirect-dispatch, or bulk-copy paths.
