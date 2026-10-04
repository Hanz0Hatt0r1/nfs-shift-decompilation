# Phase 707 — native FUN_007682c0 BODY0 delta consumer

## Playable-slice blocker removed

Phase 696 narrowed `FUN_007682c0` to a typed effect:

```text
gate_open
accumulator_y_delta
```

but deliberately left the final BODY `+0x50` application as an external
consumer because concrete retail BODY ownership was not proven at that time.

Process 1 PR #1208 closes that exact identity gap:

```text
global vehicle base
  -> +0x339c
  -> BODY-array owner
  -> BMW chassis BODY 0
```

Phase 707 consumes the positive Phase 703 handoff and replaces the external
`Fun007682c0AccumulatorDeltaConsumer` with a native persistent BODY0 mutation.
This reduces the deepest provider-session boundary set from nine external
providers to eight.

## Source-backed application

Phase 380 machine evidence proves that `FUN_007682c0` adds its final scalar only
to BODY accumulator `+0x50`.

The recovered persistent BODY ABI identifies:

```text
accumulator_a = f64x3 at +0x48/+0x50/+0x58
```

Phase 707 therefore performs exactly:

```text
BODY[selected=0].f64(+0x50) += accumulator_y_delta
```

with finite-value checks, exact `0x170` record cardinality and bounds checks.
It does not assign a new physical field name or introduce host sqrt/trig math.

## Ordering

The visible retail anchor order places `FUN_007682c0` at the end of the
`FUN_0076d100` required anchor sequence and before the corresponding
`FUN_00765470` half-step.

To preserve that order, the existing composed chain gains one optional
`Fun0076d100PostAnchorBodyStateMutator`:

```text
FUN_0076d100 required anchors
  -> motion_read_gate produces typed effect
  -> Phase 707 mutates chain-owned BODY0 +0x50
  -> FUN_00765470 half-step receives the mutated persistent BODY bytes
```

The mutator defaults to empty, so all pre-707 callers retain their prior
behavior and ABI surface.

## Retail BODY identity gate

The new chain does not infer BODY0 from index convention alone. Before any pass
provider is invoked it calls:

```text
build_vehicle_body_identity_selection_from_global_owner(...)
```

The existing Phase 703 validator requires all positive handoff flags, rejects
the obsolete update-child pointer-equality gate and admits only the retail BMW
chassis BODY index 0.

Blocked or inconsistent identity therefore fails before provider side effects.

## Persistent runtime transaction

`SHIFT.NativeBody0DeltaRuntime/1` executes the Phase 707 chain against the
currently committed `ExplicitOuterUpdateRuntimeState::body_bytes`.

Only after the complete two-pass chain succeeds and new pose snapshots decode
does it commit:

- final BODY bytes;
- pose snapshots;
- explicit update count/generation;
- existing outer-update telemetry.

A provider, native delta, solver, or pose-decode failure leaves the previous
runtime state committed.

## Provider session v2

`SHIFT.NativeVehicleProviderSession/2` has eight external boundaries:

1. `FUN_00765c40` complete anchor;
2. `FUN_00758b50` wheel update;
3. `FUN_00766510` contact response;
4. `FUN_007675f0` input provider;
5. `FUN_007682c0` typed effect provider;
6. `FUN_007afdd0` scalar-provider factory;
7. `FUN_00765470` half-step refresh bundle;
8. `FUN_007b8810` post-half-step refresh.

There is no external motion-read delta consumer in v2. The old
`SHIFT.NativeVehicleProviderSession/1` remains available for compatibility and
continues to expose nine boundaries.

## Regression requirements

The native Phase 707 check proves:

- exact standalone f64 update of BODY0 `+0x50`;
- BODY1 `+0x50` remains unchanged by the standalone consumer;
- blocked Phase 703 identity fails before provider side effects;
- pass 0 half-step observes the already-applied BODY0 delta;
- closed pass gate causes no native delta application;
- the v2 session reports eight external provider boundaries;
- persistent BODY state commits transactionally;
- participant admission failure occurs before provider side effects;
- explicit outer update remains separate from `fixed_step()` scheduling.

The dedicated workflow also rebuilds/runs the legacy Phase 696/701 regressions
to ensure the optional post-anchor mutator did not change existing paths.

## Remaining blockers

Phase 707 does not close:

- `FUN_007682c0` typed effect production itself;
- `FUN_007afdd0` machine scalar production;
- `FUN_00765470` field producer ownership/refresh schedule;
- outer-update cadence ownership;
- initial retail BODY record construction;
- `SHIFT.BMWBody0BindFrameProof/1`;
- Phase 706 transform commit scheduling;
- camera follow.

Process 1 PR #1210 has narrowed the BODY0 bind proof further by binding the
`FUN_007b7840` pose-writer parameters to physical ABI storage, but semantic
BODY/origin/basis roles and any required stack-slot provenance remain
fail-closed.

No original game execution and no new runtime capture are used.
