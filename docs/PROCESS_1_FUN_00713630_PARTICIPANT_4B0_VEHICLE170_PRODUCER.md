# Process 1A — positive selected `PhysicsParticipant+0x4b0` producer proof

## BLOCKER

P1.1a was the last Process 1A ownership blocker. Config globals and sample-history scheduling were already closed, but the selected participant `+0x4b0` runtime producer remained unresolved.

## OUTPUT

The producer is `FUN_007927c0` operating on the embedded Vehicle at selected participant `+0x340`.

The authoritative source contains the direct assignment:

```text
*(undefined4 *)((int)this + 0x170) = param_2[1]
```

Retail machine transfer implements the same store at `0x007927ee`: `EAX` is `ESI+0x16c`, then `fstp dword ptr [EAX+0x4]`, so the effective destination is receiver `+0x170`.

The selected participant identity join is exact. `FUN_00713340` iterates the same `manager+0x140`, stride-`0x1fa0` records used by `FUN_00713630`. At `0x007133d3` it dereferences `record[0]` to the actual participant, adds `0x340`, and calls `FUN_007927c0` at `0x007133db`. Therefore:

```text
selected participant + 0x340 + 0x170 = selected participant + 0x4b0
```

This is not setup-only constant state. The runtime message path at `0x00710563` also calls `FUN_007927c0` on `record[0]+0x340` while passing message payload storage as `param_2`; the `+0x170` value therefore has an explicit runtime materialization path.

This corrects one stale field in `SHIFT.Fun00713630Participant4b0SubobjectAliasFrontier/1`: its `direct_subobject_plus_0x170_store_found=false` conclusion is superseded. Its participant/subobject identity proof remains valid and is reused here.

## GATES_CHANGED

- selected participant runtime `+0x4b0` writer: **closed**;
- seven config inputs: **already closed** by `SHIFT.Fun00713630PhysicsTweakerMaterialization/1`;
- sample-history scheduling: **already closed** by `SHIFT.Fun00713630UpstreamDirectSurface/1`;
- P1.1a: **complete**;
- P1.1c: **complete**;
- P1.1: **not yet promoted in this slice**;
- `contact_response` removal: **not yet authorized**;
- provider count: **7**.

## WHY P1.1 IS STILL FAIL-CLOSED HERE

`SHIFT.Fun00766510ResidualOwnershipFrontier/1` requires an explicit Process 1 handoff after the remaining P1.1a ownership closes. This producer proof deliberately does not merge proof closure and consumer authorization into one implicit transition.

## NEXT_STEP

Publish the explicit final Process 1 P1.1 handoff joining P1.1a=true with the already closed P1.1c tail, preserving exact retail order for Process 2. That handoff may authorize Process 2 to consume the boundary and target provider count 7 -> 6.
