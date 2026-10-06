# Phase 708 — provider frontier refresh after retail identity

## Playable-slice blocker reduced

Phase 707 removes caller-injected BODY-owner identity from the retail BMW
transform path. Process 3 Phase 649 provides the freshness-gated live Vulkan
sink. The original Phase 708 refresh removed those stale blockers from the
machine-readable Phase 699 provider graph.

S5 subsequently closes one more cross-chain dependency: the default-mode retail
outer scheduler owner/cadence. This document now records that later coordination
closure without changing the historical Phase 708 provider result.

No physics producer semantics are promoted here.

## Current result

`SHIFT.NativeVehicleExternalProviderFrontier/1` now records:

```text
retail BODY-owner identity       CLOSED by Process 1 #1208 + Phase 707
renderer live transform sink     CLOSED through Process 3 Phase 649
retail outer cadence owner       CLOSED by SHIFT.RetailOuterUpdateCadence/1
atomic explicit outer dispatch   READY in NativeVehicleProviderSession
selected-session inner rate      STILL BLOCKED on exact PC PhysicsTweaker payload
BODY0 pose-writer physical ABI   READY by Process 1 #1210
BODY0 bind semantic witness      STILL BLOCKED
external physics providers       9
implement_now                    0
```

The nine provider APIs are unchanged.

## Important narrowing

Three stale requests are now excluded from the active blocker graph:

1. `FUN_00765470` half-step refresh no longer asks for BODY-owner receiver
   provenance. #1208 already closed that identity edge. The remaining request is
   producer ownership and exact refresh/reuse timing for each composite field.
2. `FUN_007682c0` delta application no longer asks for global vehicle/BODY-owner
   identity. It asks only for exact destination BODY pointer/record provenance at
   the `+0x50` application site and a join of that destination to proven retail
   chassis BODY 0.
3. Outer-update cadence ownership is no longer a Process 1 request. S5 proves
   default-mode `MWL::Core::cPhysicsManager` ownership, nominal 30 Hz, the
   distinct quantized 33 ms timing gate, and one steady scheduler invocation per
   default manager dispatch.

The cadence closure does **not** supply the selected-session PhysicsTweaker tick
rate. Those are separate gates.

## Retail scheduler state after S5

Positive handoff:

```text
SHIFT.RetailOuterUpdateCadence/1
  owner                 MWL::Core::cPhysicsManager
  nominal frequency     30 Hz
  timing gate           33 ms
  scheduler calls       1 / steady default dispatch
  accumulator increment 0.03333333507180214 s
  authority             RetailEvidence
```

Process 2 consumer:

```text
NativeVehicleProviderSession::execute_retail_outer_dispatch(runtime, scheduler)
```

That transaction admits the recovered outer accumulator contribution, derives
the exact recovered batch count once a loaded rate exists, executes persistent
BODY substeps at `1/rate`, and commits the accumulator only after a successful
batch. Missing-rate or deep-provider failure rolls back to the pre-dispatch
state.

Preserved negative claims:

```text
selected_session_inner_rate_ready = false
fixed_step_auto_schedule_allowed = false
render_loop_equated_to_outer_dispatch = false
```

Host 1/60 and the BManager 10 ms poll are not substitutes for retail cadence.
No catch-up/drop behavior is invented.

## Transform blocker

Process 1 #1210 proves `SHIFT.BMWBody0BindPoseWriterABI/1`, but it leaves all
semantic bind claims false:

```text
BODY0_pointer_proven = false
BODY0_bind_origin_proven = false
BODY0_bind_basis_proven = false
BODY0_bind_frame_proof_ready = false
```

Process 2 therefore continues to reject a retail Phase 704/705/706 world matrix
until a positive `SHIFT.BMWBody0BindFrameProof/1` exists.

## Renderer state

The graph treats these as closed infrastructure:

```text
Phase 646  dynamic transform core
Phase 647  live Vulkan vertex upload
Phase 648  runtime frame wiring for explicit regression producer
Phase 649  current Phase706 snapshot -> freshness-gated Vulkan upload
```

Phase 649 is a consumer, not a retail transform producer. It does not make the
missing BODY0 bind witness or transform commit schedule positive.

## Preserved guards

The current coordination graph preserves:

- two half-steps;
- persistent BODY state;
- participant admission;
- missing-provider failure before side effects where the existing APIs require it;
- no automatic fixed-step/render-loop retail scheduling;
- no host `sqrt`, `sin`, or `cos` substitution;
- no semantic inference from pose-writer physical ABI;
- no BODY0 bind synthesis;
- no constructor-default 180 Hz promotion;
- no guessed selected-session PhysicsTweaker rate;
- no original game execution;
- no new runtime capture.

## Next work

After the S5 cadence closure, Process 2 should consume the first genuinely
positive proof among:

1. the exact PC `physicstweaker.xml` payload -> decoded SHA-256 -> unique selected-session tick rate;
2. one of the nine provider producer rows;
3. semantic `SHIFT.BMWBody0BindFrameProof/1`;
4. retail resources -> concrete initial `0x170` BODY records.

Until one changes state, another scheduler/renderer transport adapter would not
shorten the playable-slice blocker graph.
