# Process 1 — `FUN_00765c40` residual ownership frontier

## BLOCKER

P1.2 is the Process 1 proof gate for Process 2 P2.4. The active selected-session boundary still represents the complete residual `FUN_00765c40` pass, so Process 2 cannot narrow or remove it while collision/world lookup behavior or source-visible side effects remain unowned.

The queue text previously grouped three concerns together: collision-provider ownership, four wheel `+0x738` load terms, and residual side effects. The load-term item is no longer open: `SHIFT.Fun00765c40LoadTerms/1` positively owns all four values and their pass order.

## INPUT

This slice introduces no new machine-code or decompiler claim. It joins existing PC-retail-backed contracts:

- `SHIFT.Fun00765c40SelectedBMWWorldPosition/1` — selected BMW query world position is native-owned per pass;
- `SHIFT.Fun00765c40QueryCacheLifetime/1` — persistent `HDVehicle+0x38dc` query-cache lifetime is native-owned;
- `SHIFT.Fun00765c40SelectedBMWQueryFallback/1` — selected BMW `HDVehicle+0x38e8` miss fallback setup/value is owned;
- `SHIFT.Fun00765c40CollisionOutputHandoff/1` — the `FUN_007b0710` query/output boundary and downstream scalar handoff are typed, while collision-provider implementation remains external;
- `SHIFT.Fun00765c40LoadTerms/1` — all four wheel `+0x738` load terms are source/machine-backed and typed.

PC retail remains the semantic authority.

## OUTPUT

Adds `SHIFT.Fun00765c40ResidualOwnershipFrontier/1` as the current fail-closed P1.2 selection contract.

The selected BMW pre-query surface is already closed far enough that it must not be rediscovered:

```text
selected per-pass world position       CLOSED
persistent +0x38dc cache lifetime      CLOSED
selected +0x38e8 miss fallback         CLOSED
typed FUN_007b0710 query/output seam   CLOSED AS A SEAM, provider implementation still external
four wheel +0x738 load terms           CLOSED
```

The load-term geometry is fixed as:

```text
wheel array base = HDVehicle+0x400
count            = 4
stride           = 0xa80
per-wheel field  = +0x738 f64
HDVehicle lanes  = +0xb38/+0x15b8/+0x2038/+0x2ab8
```

Older Phase739–741 contracts correctly recorded load terms as external when those phases were authored. The later `SHIFT.Fun00765c40LoadTerms/1` proof supersedes only that historical open item. It does not make the collision/world provider native and it does not prove the absence of other writes.

## Remaining P1.2 proof

Only two proof classes remain in the Process 1 frontier:

1. **P1.2a — collision/world lookup below `FUN_007b0710`.** The query record and returned result are typed, but the retail object/call performing the actual lookup has not been positively owned as an internal implementation. This may ultimately remain an explicit typed provider if the source owner cannot yet be internalized.
2. **P1.2b — residual `FUN_00765c40` side effects.** Every source-visible write outside the already-closed query-input/output and load-term surfaces must be classified before the complete pass callback can be removed. Lack of a typed field is not evidence that no write exists.

## CONSUMER

Process 2 P2.4 should consume this frontier and stop treating the four `+0x738` load terms as a missing Process 1 proof. Native implementation/provider reduction must remain blocked on P1.2a/P1.2b.

## GATES_CHANGED

- selected BMW world-position ownership: **closed**;
- `+0x38dc` cache lifetime: **closed**;
- selected `+0x38e8` fallback: **closed**;
- four wheel `+0x738` load-term ownership: **closed**;
- collision/world provider implementation: **open**;
- exhaustive residual side-effect audit: **open**;
- P1.2 complete: **false**;
- `FUN_00765c40` provider removal authorized: **false**;
- external-provider count: **7**.

## LIMITS

This join does not assign a physical name to the collision provider, does not infer an implementation from the typed `FUN_007b0710` ABI, and does not claim that unknown side effects are absent. It also does not decrement the provider count.

## TESTS

`tests/test_process1_fun_00765c40_residual_ownership_frontier.py` cross-checks the joined positive contracts, four-wheel load geometry, exact remaining P1.2 target set, and fail-closed provider-removal gate.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Trace the retail collision/world lookup object/call below `FUN_007b0710`, while separately inventorying `FUN_00765c40` writes that are not already represented by the query handoff or four closed load terms.
