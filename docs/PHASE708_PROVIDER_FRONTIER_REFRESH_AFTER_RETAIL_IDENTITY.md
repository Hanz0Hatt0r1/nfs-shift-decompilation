# Phase 708 — provider frontier refresh after retail identity

## Playable-slice blocker reduced

Phase 707 removes caller-injected BODY-owner identity from the retail BMW
transform path. Process 3 Phase 649 already provides the freshness-gated live
Vulkan sink. The machine-readable Phase 699 provider graph still described both
of those boundaries as pending, which would send subsequent work toward already
closed proofs.

Phase 708 updates only coordination state. It does not add physics behavior.

## Result

`SHIFT.NativeVehicleExternalProviderFrontier/1` now records:

```text
retail BODY-owner identity       CLOSED by Process 1 #1208 + Phase 707
renderer live transform sink     CLOSED through Process 3 Phase 649
BODY0 pose-writer physical ABI   READY by Process 1 #1210
BODY0 bind semantic witness      STILL BLOCKED
external physics providers       9
implement_now                    0
```

The nine provider APIs are unchanged.

## Important narrowing

Two stale proof requests are removed:

1. `FUN_00765470` half-step refresh no longer asks for BODY-owner receiver
   provenance. #1208 already closed that identity edge. The remaining request is
   producer ownership and exact refresh/reuse timing for each composite field.
2. `FUN_007682c0` delta application no longer asks for global vehicle/BODY-owner
   identity. It now asks only for exact destination BODY pointer/record
   provenance at the `+0x50` application site and a join of that destination to
   proven retail chassis BODY 0.

That distinction prevents a global BODY-domain proof from being overread as
proof of the exact local mutation target.

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

The graph now treats these as closed infrastructure:

```text
Phase 646  dynamic transform core
Phase 647  live Vulkan vertex upload
Phase 648  runtime frame wiring for explicit regression producer
Phase 649  current Phase706 snapshot -> freshness-gated Vulkan upload
```

Phase 649 is a consumer, not a retail transform producer. It does not make the
missing BODY0 bind witness or transform commit schedule positive.

## Preserved guards

Phase 708 preserves:

- two half-steps;
- persistent BODY state;
- participant admission;
- missing-provider failure before side effects where the existing APIs require
  it;
- explicit outer update only;
- no host `sqrt`, `sin`, or `cos` substitution;
- no semantic inference from pose-writer physical ABI;
- no BODY0 bind synthesis;
- no original game execution;
- no new runtime capture.

## Next work

After this refresh, Process 2 should consume the first genuinely positive proof
among:

1. one of the nine producer rows;
2. semantic `SHIFT.BMWBody0BindFrameProof/1`;
3. exact outer-update cadence owner;
4. retail resources -> concrete initial `0x170` BODY records.

Until one changes state, adding another transform/renderer adapter would not
shorten the playable-slice blocker graph.
