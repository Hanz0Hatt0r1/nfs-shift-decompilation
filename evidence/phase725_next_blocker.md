# Phase 725 next blocker

Phase 725 makes the active session boundary match what is actually proven: the external complete `FUN_00765c40` pass returns a typed `Fun00765c40ExternalPassResult`, whose currently consumed downstream payload is the four wheel `+0x738` load terms.

## NEXT_STEP

Recover the exact upstream wheel world-position producer used by `FUN_00765c40` and the collision-provider/query behavior that turns those positions into the source-visible wheel/contact state.

Do not infer a world transform from the already-closed BODY0/VHF renderer path: that path proves vehicle rendering transforms, not the wheel-contact query producer used inside `FUN_00765c40`.

Preserve these already-closed/native boundaries:

- native `FUN_00758ad0` contact-factor arithmetic;
- native `FUN_007b0710` collision-query record contract;
- native wheel query/response join;
- typed `Fun00765c40LoadTerms` output ownership;
- Phase 724 `FUN_007682c0` gate/steering/+0x4054/projection/difficulty closure;
- selected-session retail scheduler and BODY0/VHF transform chain.

Until the missing producer/provider joins are source-backed, keep the complete `FUN_00765c40` pass external and keep the active provider count at seven.
