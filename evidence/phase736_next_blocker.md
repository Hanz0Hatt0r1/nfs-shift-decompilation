# Phase 736 next blocker

Phase 736 removes the last directly supplied scalar from production `ContactOuterSessionInput`. The contact-outer provider now supplies an earlier source boundary: the fixed three-record `FUN_00759c90` input set.

The next ownership blocker is those records themselves. PC retail places the records at `HDVehicle+0x7f0` and advances by `0x150` double elements (`0xa80` bytes) for exactly three iterations. Their current producers/refresh timing are not yet owned by the native selected-session path.

A safe next slice should:

1. trace writers/refresh owners for the three record slots and the consumed fields `-0x08`, `+0x00`, `+0x98`, and `+0xb0`;
2. preserve the exact per-pass ordering before `FUN_00759c90` executes;
3. use Xbox `sub_825939F0 -> sub_825899C0` as a search oracle only, confirming all PC offsets against retail x86;
4. internalize record storage only if the writer/lifetime join is source-backed;
5. otherwise prefer a bounded later target in the `FUN_00753810`/`FUN_007ba9e0` path rather than guessing record semantics.

The active top-level external-provider count remains seven until an entire provider boundary can be removed.
