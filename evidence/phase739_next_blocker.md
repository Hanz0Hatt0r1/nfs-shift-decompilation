# Phase 739 next blocker

The selected Silverstone + BMW M3 E36 `FUN_00765c40` query world position is now native-owned per pass. The complete external pass boundary still remains because it also owns data/behavior not closed by Phase739:

1. four `Fun00765c40LoadTerms` produced by the existing wheel loop;
2. the query cache handle supplied to native `FUN_007b0710` record construction;
3. `HDVehicle+0x38e8` miss fallback;
4. the collision-provider implementation below the typed query record;
5. residual `FUN_00765c40` side effects not represented by the already-native contact-factor/query arithmetic.

The next bounded slice should separate one of those ownership groups from `Fun00765c40ExternalPassResult` using PC source/machine evidence. Prefer cache/fallback lifetime or the already-typed load-term producer before attempting the unnamed collision-provider implementation.

Do not reduce the active provider count from seven until the complete pass callback has no remaining source-backed behavior that must still execute externally.
