# Process 1 — `FUN_00766510` residual ownership frontier

## BLOCKER

P1.1 is still the first Process 1 blocker preventing Process 2 from removing the top-level `contact_response` provider and reducing the external-provider frontier from 7 to 6.

Several items still listed in the original V6 queue are no longer open: the response configuration, earlier `+0x3b20` branch, optional `+0x3bc8/+0x3cxx` branch, primary response application/caller delta, and shared reference-vector ownership have all received positive contracts. This document joins those merged facts and narrows P1.1 to the remaining proof surface.

## INPUT

No new PC semantic claim is introduced by this join. It consumes already-merged PC-retail-backed contracts, including:

- `SHIFT.Fun00766510ResponseConfigOwnership/1`;
- `SHIFT.Fun00766510EarlyResponseBranchOwnership/1`;
- `SHIFT.Fun00766510OptionalResponseBranchOwnership/1`;
- `SHIFT.Fun00766510PrimaryResponseApplication/1` and active `/2` extension;
- `SHIFT.Fun00766510SharedReferenceVector/1`;
- the existing native `FUN_00758fc0` per-record and two-record pair contracts.

PC retail 1.02 remains semantic authority. Xbox recompilation remains navigation/corroboration only.

## OUTPUT

Adds `SHIFT.Fun00766510ResidualOwnershipFrontier/1` as a fail-closed coordination/evidence join.

The residual P1.1 proof surface is now explicitly:

1. **P1.1a — `FUN_00713630` dynamic writer inputs.** Phase747 proves that `FUN_00713630` refreshes actual-participant `+0x16b4/+0x16b8/+0x16bc` under `FUN_007144a0` scheduling, but the upstream dynamic X/Z generator state is still not owned. These lanes must not be frozen as setup constants.
2. **P1.1b — later `+0x3a28/+0x3a40` direct response block.** The Phase746 whole-function inventory identifies this caller contribution, but there is no positive owner/config/source-order contract for it yet.
3. **P1.1c — final cumulative response plus residual state/diagnostic writes.** `HDVehicle+0x40a0/+0x40a8/+0x40b0` is known to start at zero and receive several contribution classes, but the whole accumulator and later conditional writes still need one exhaustive preservation contract.

The known accumulator contribution classes remain:

```text
earlier +0x3b08/+0x3b20 direct block
optional +0x3c60 direct block
up to two FUN_00758fc0 record contributions
primary +0x38f0/+0x3950 direct block
later +0x3a28/+0x3a40 direct block
final transformed cumulative response vector
```

## CONSUMER

Process 2 P2.3 consumes the final positive P1.1 handoff. Until P1.1a–c are closed, Process 2 must keep `contact_response` external.

## GATES_CHANGED

- stale P1.1 subtargets already covered by merged positive contracts: **retired from active queue**;
- residual P1.1 frontier: **explicit and machine-readable**;
- P1.1 complete: **false**;
- `contact_response` removal authorized: **false**;
- external-provider count: **7**;
- reduction target after Process 2 consumption: **6**.

## LIMITS

This join does not infer the dynamic X/Z generator, does not assign physical names to the later direct-response block, and does not classify residual writes that lack a positive source-backed contract. It therefore cannot itself authorize provider removal.

## TESTS

`tests/test_process1_fun_00766510_residual_ownership_frontier.py` verifies the positive upstream contracts required by the join, the exact residual subtargets, the six known accumulator contribution classes, and the fail-closed provider-removal gate.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Trace the upstream dynamic X/Z generator state consumed by `FUN_00713630`. After that, close the later `+0x3a28/+0x3a40` block and publish an exhaustive final accumulator/state-write preservation contract for Process 2 P2.3.
