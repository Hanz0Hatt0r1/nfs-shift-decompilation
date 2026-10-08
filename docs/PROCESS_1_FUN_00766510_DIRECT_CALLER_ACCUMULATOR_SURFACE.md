# Process 1 — direct `FUN_00766510` caller-accumulator surface

## BLOCKER

P1.1c still requires an exhaustive preservation contract for `HDVehicle+0x40a0/+0x40a8/+0x40b0` before Process 2 can remove the top-level `contact_response` provider.

Phase 746 proved that the whole function contains exactly four direct caller-side `FUN_00753650` cross-product add sites, in addition to two `FUN_00758fc0` auxiliary calls and one final transformed-vector add. Until now those four direct sites were proven in separate branch contracts but were not joined as a complete surface.

## INPUT

This slice introduces no new PC semantic or machine-code claim. It joins already-positive PC-retail-backed evidence:

- `SHIFT.Fun00766510PrimaryCallerAccumulator/1` — inventory of exactly four direct `FUN_00753650` sites, two auxiliary calls and one final vector add;
- `SHIFT.Fun00766510EarlyResponseBranchOwnership/1` — early `+0x3b08/+0x3b20` direct site, caller accumulator write at source line 759558;
- `SHIFT.Fun00766510OptionalResponseBranchOwnership/1` — gated `+0x3c60` direct site, caller accumulator write at source line 759621;
- `SHIFT.Fun00766510PrimaryCallerAccumulator/1` — primary `+0x38f0/+0x3950` site, source window 759686–759692 and frozen cross/store machine span;
- `SHIFT.Fun00766510LaterResponseBranchOwnership/1` — later `+0x3a28/+0x3a40` site, `FUN_00753650` at 759731 and caller accumulation at 759732.

PC retail 1.02 remains semantic authority. Xbox recompilation is not required for this join.

## OUTPUT

Adds `SHIFT.Fun00766510DirectCallerAccumulatorSurface/1`.

The direct caller-side surface is now exhaustively accounted for:

```text
expected direct FUN_00753650 add sites = 4
accounted direct FUN_00753650 add sites = 4

1. early    +0x3b08/+0x3b20
2. optional +0x3c60
3. primary  +0x38f0/+0x3950
4. later    +0x3a28/+0x3a40
```

Each site already has a positive owner/order contract, and the primary site additionally has the native `caller_accumulator_delta` implementation.

This closes the question “are there unclassified direct `FUN_00753650` writes to the caller accumulator?” with **no**. It does not collapse those branches into one guessed physical semantic.

## P1.1c residual after this slice

The complete accumulator is still not closed. The remaining bounded proof is:

1. join the two already-native `FUN_00758fc0` auxiliary contributions to the complete caller-accumulator preservation contract at their exact `FUN_00766510` scheduling points;
2. source-lock the final transformed cumulative-response vector add that reaches both BODY0 `+0x48/+0x50/+0x58` and caller `+0x40a0/+0x40a8/+0x40b0`;
3. classify every residual conditional state/diagnostic write after the response branches.

The auxiliary pair itself is already positive: exactly two records at `+0x37d8` and `+0x3858`, with native per-record arithmetic and pair ordering. This slice deliberately does not invent the missing larger scheduling/tail contract from that fact.

## CONSUMER

Process 2 P2.3 may consume the direct-site closure. It must still keep `contact_response` external until the remaining P1.1 proof is positive.

## GATES_CHANGED

- all four direct caller-side `FUN_00753650` accumulator sites accounted: **true**;
- direct caller cross-product surface complete: **true**;
- whole caller accumulator complete: **false**;
- P1.1c complete: **false**;
- `contact_response` removal authorized: **false**;
- external-provider count: **7**.

## LIMITS

No physical semantic name is assigned to the accumulator. No selected-session values are synthesized. This join does not prove the final transformed-vector add or the complete residual diagnostic/state-write tail.

## TESTS

`tests/test_process1_fun_00766510_direct_caller_accumulator_surface.py` cross-checks the four-site inventory against the existing early, optional, primary and later evidence and verifies that provider removal remains fail-closed.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Recover and source-lock the remaining P1.1c tail beginning with the exact `FUN_00758fc0` caller scheduling and final transformed cumulative-response vector add, then fold the residual diagnostic/state writes into the same preservation contract.
