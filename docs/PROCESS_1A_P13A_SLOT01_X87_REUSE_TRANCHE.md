# Process 1A / P1.3A — x87 reuse tranche closure

Merged x87 frontier #1738 contains 18 shallow `FLDZ -> FST/FSTP` candidates. This tranche closes the nine candidates whose receiver or exact destination range is already fixed by merged P1A machine contracts, avoiding duplicate reverse engineering.

## Closed candidates

- `FUN_00763570`: entry receiver is retained in `EDI`; both zero stores are `+0x41d8`.
- `FUN_00770e80`: entry receiver is retained in `ESI`; zero stores are `+0x4024..+0x402c` and `+0x3ff0..+0x4018`.
- `FUN_00755a60`: exact wheel receiver; zero store is wheel-local `+0x850`, not selected local `+0x538`.
- `FUN_00760b50`: exact wheel receiver; zero stores are wheel-local `+0x868/+0x8b0`.
- `FUN_0076e560`: HDVehicle-root receiver; zero stores are `+0x3e50/+0x3e58`.
- `FUN_00647a10`: fixed singleton `0x00c29640` constructor tree.
- `FUN_0070fae0`: Physics Manager singleton `0x00c104e0`, vptr `0x00b04524`.
- `FUN_0076f030`: HDVehicle-root receiver; zero store is only `+0x18`.
- `FUN_0088f110`: fixed singleton nested receiver `0x00c29b98`.

All nine are negative for selected `HDVehicle+0x938/+0x13b8`. Numeric reachability is never used as identity; either exact receiver provenance or exact disjoint destination range closes each item.

## Remaining x87 frontier

Nine candidates still require new receiver/output tracing: `FUN_00766510`, `FUN_0075c0d0`, `FUN_007aa940`, `FUN_007b8630`, `FUN_0075ada0`, `FUN_0075afc0`, `FUN_007876e0`, `FUN_007ade70`, and `FUN_007b7840`.

Therefore x87 semantics, SSE/vector copy-init, deeper direct aliases, indirect/callback aliases, slot0/slot1, aggregate P1.3 and provider removal all remain fail-closed; provider count remains 7.
