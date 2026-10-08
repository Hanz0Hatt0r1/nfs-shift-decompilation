# Process 1 — `FUN_00765c40` residual ownership frontier

## BLOCKER

P1.2 is the Process 1 proof gate for Process 2 P2.4. The active selected-session boundary still represents the complete residual `FUN_00765c40` pass, so Process 2 cannot narrow or remove it while collision/world lookup behavior or source-visible side effects remain unowned.

The queue text previously grouped collision-provider ownership, four wheel `+0x738` load terms, and residual side effects. The load-term item is closed, and the caller-visible `FUN_007b0710` ABI is now explicitly separated from the still-unknown lower scene-query implementation.

## INPUT

Current positive PC-retail-backed contracts include:

- `SHIFT.Fun00765c40SelectedBMWWorldPosition/1` — selected BMW query world position is native-owned per pass;
- `SHIFT.Fun00765c40QueryCacheLifetime/1` — persistent `HDVehicle+0x38dc` query-cache lifetime is native-owned;
- `SHIFT.Fun00765c40SelectedBMWQueryFallback/1` — selected BMW `HDVehicle+0x38e8` miss fallback setup/value is owned;
- `SHIFT.Fun00765c40CollisionOutputHandoff/1` — the `FUN_007b0710` query/output boundary and downstream scalar handoff are typed;
- `SHIFT.Fun00765c40LoadTerms/1` — all four wheel `+0x738` load terms are source/machine-backed and typed;
- `SHIFT.Fun007b0710CollisionProviderFrontier/1` — `FUN_007b0710` caller-visible ABI is closed and existing evidence pins `FUN_0074f560` as the known lower fallback-query surface while leaving the actual scene-query provider open.

PC retail remains the semantic authority.

## OUTPUT

`SHIFT.Fun00765c40ResidualOwnershipFrontier/1` remains the fail-closed P1.2 selection contract, now with P1.2a narrowed below the already-recovered query ABI.

The selected BMW/query/load surface must not be rediscovered:

```text
selected per-pass world position       CLOSED
persistent +0x38dc cache lifetime      CLOSED
selected +0x38e8 miss fallback         CLOSED
typed FUN_007b0710 query/output seam   CLOSED AS CALLER-VISIBLE ABI
known lower fallback-query surface     FUN_0074f560
four wheel +0x738 load terms           CLOSED
exact scene-query provider             OPEN
```

The load-term geometry remains:

```text
wheel array base = HDVehicle+0x400
count            = 4
stride           = 0xa80
per-wheel field  = +0x738 f64
HDVehicle lanes  = +0xb38/+0x15b8/+0x2038/+0x2ab8
```

## Remaining P1.2 proof

Only two proof classes remain:

1. **P1.2a — collision/world lookup implementation at or below `FUN_0074f560` / the scene-query boundary.** `FUN_00765c40 -> FUN_007b0710` caller-visible behavior is no longer the search target. The missing proof is the actual provider object/pointer domain and lower call/dispatch that performs the retail lookup, plus provenance back to the recovered 0x58-byte surface-record boundary.
2. **P1.2b — residual `FUN_00765c40` side effects.** Every source-visible write outside the already-closed query-input/output and load-term surfaces must be classified before the complete pass callback can be removed.

## CONSUMER

Process 2 P2.4 should consume the closed query ABI, selected inputs, and load terms. Native collision-provider implementation/provider reduction must remain blocked on P1.2a/P1.2b.

## GATES_CHANGED

- selected BMW world-position ownership: **closed**;
- `+0x38dc` cache lifetime: **closed**;
- selected `+0x38e8` fallback: **closed**;
- four wheel `+0x738` load-term ownership: **closed**;
- `FUN_007b0710` caller-visible ABI: **closed**;
- `FUN_0074f560` known lower fallback-query surface: **pinned**;
- exact scene-query provider implementation: **open**;
- exhaustive residual side-effect audit: **open**;
- P1.2 complete: **false**;
- `FUN_00765c40` provider removal authorized: **false**;
- external-provider count: **7**.

## LIMITS

No physical provider name, PhysX class, scene object, virtual slot, new source line, or machine span is invented. `FUN_0074f560` is not promoted beyond the lower fallback-query role already present in Phase 370/666 evidence.

## TESTS

`tests/test_process1_fun_00765c40_residual_ownership_frontier.py` verifies the joined positive contracts and narrowed P1.2a/P1.2b target set. `tests/test_process1_fun_007b0710_collision_provider_frontier.py` separately pins the lower provider frontier against existing Phase 370/666 evidence.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Start targeted PC static review at `FUN_0074f560` and its lower scene-query dispatch while separately inventorying `FUN_00765c40` writes that are not already represented by the query handoff or four closed load terms.
