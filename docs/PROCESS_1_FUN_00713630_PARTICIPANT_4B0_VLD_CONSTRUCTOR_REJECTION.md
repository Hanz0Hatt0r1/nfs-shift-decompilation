# Process 1A — reject `0x007c0fe2` from the participant `+0x4b0` frontier

## BLOCKER

The current `SHIFT.Fun00713630Participant4b0Frontier/1` still has direct-displacement writer sites whose base-object identity is unjoined. One is `0x007c0fe2` inside `FUN_007c0db0`.

## OUTPUT

Retail machine transfer roots this site to the separately allocated `0x3848` VehicleLoadData-family object, not the selected `0x2b90` PhysicsParticipant.

`FUN_007c3170` captures its incoming object in `ESI`, then calls `FUN_007c0db0` with `ECX = ESI + 0x8`:

```text
0x007c318a  ESI = ECX
0x007c31a3  ECX = ESI + 0x8
0x007c31aa  call FUN_007c0db0
```

The candidate store in that callee is:

```text
0x007c0fe2  [ESI+0x4b0] = 0
```

Therefore this store targets the `+0x8` nested subobject and maps to allocation `+0x4b8`, not to PhysicsParticipant `+0x4b0`.

Both exact constructor roots independently allocate `0x3848` bytes before `FUN_007c3170`:

- `FUN_0076df50` stores the constructed pointer at `HDVehicle+0x66b4`;
- `FUN_00798df0` stores the constructed pointer at selected subobject `+0x1d00`.

This matches the existing positive VehicleLoadData ownership contract used by the earlier `FUN_007c3b00` rejection.

## GATES_CHANGED

- direct candidate `0x007c0fe2`: **rejected**;
- exact receiver/constructor identity for this candidate: **closed**;
- unresolved direct-displacement candidates: **13**;
- actual selected participant `+0x4b0` runtime writer: **open**;
- P1.1a/P1.1: **incomplete**;
- `contact_response` provider removal: **not authorized**;
- external provider count: **7**.

## NEXT_STEP

Continue exact receiver-provenance adjudication of the remaining 13 direct-displacement writer sites. Prefer constructor/static-init roots where the identity can be closed without widening into speculative semantics.
