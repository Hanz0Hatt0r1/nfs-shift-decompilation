# Phase 740 next blocker

The `HDVehicle+0x38dc` query-cache lifetime is now session-owned and transactional.

The next bounded residual `FUN_00765c40` field is `HDVehicle+0x38e8`, used as the miss fallback after `FUN_007b0710` returns no hit.

Before internalizing it, recover and freeze:

1. the PC setup producer that writes `+0x38e8`;
2. whether its value is one-time setup state or refreshed later;
3. the exact source value/derivation for the selected BMW session;
4. the read/write ordering relative to both `FUN_0076d100` passes.

Xbox recomp may be used only as an independent navigation/corroboration source. PC retail remains authoritative.
