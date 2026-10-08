# Phase 746 next blocker

The direct `HDVehicle+0x40a0/+0x40a8/+0x40b0` delta belonging to the Phase742 primary `+0x38f0/+0x3950` response block is now native and source-locked.

The complete caller accumulator still receives other contributions in exact retail order:

1. the earlier `+0x3b08/+0x3b20` direct response block;
2. an optional `+0x3c60` direct application behind the source-visible `+0x3bc8` / negative-local-Z branch;
3. up to two contributions inside `FUN_00758fc0` for records `this+0x37d8` and `this+0x3858`;
4. the later `+0x3a28/+0x3a40` direct response block;
5. the final transformed cumulative response vector added both to BODY0 `+0x48/+0x50/+0x58` and caller `+0x40a0/+0x40a8/+0x40b0`.

A high-value next slice is the auxiliary pair input ownership because the pair arithmetic is already native (Phase664). Recover the selected-session owner of the shared `local_d8/local_d0/local_c8` reference vector and the two setup records before scheduling it. Do not reduce the provider count until the complete `contact_response` callback can be deleted.
