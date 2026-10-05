# Playable Linux slice — blocker swarm mode

## BLOCKER

The shortest current blocker is:

```text
FUN_00795d60 render-root delta
-> exact canonical BMW_M3_E36.vhf HIERARCHY root/frame semantics
-> exact outer Vehicle-root -> BMW VHF-root relation
-> SHIFT.BMWBody0BindFrameProof/1
```

Process 1 owns the final semantic proof, but Process 2 and Process 3 must not idle when their owned queues are exhausted.

## Rule

When a downstream process has no runnable positive handoff or blocking regression, it joins the **current shortest blocker swarm** on a non-overlapping shard. The semantic owner does not change.

```text
PROCESS 3 resource shard
canonical BMW VHF hierarchy/root/frame facts
             |
             v
PROCESS 1 proof-owner shard
executable/value provenance + final relation adjudication
             |
             v
PROCESS 2 runtime-consumer shard
strict relation-stage consumer + final fail-closed admission
```

Machine-readable coordination contract:

```text
SHIFT.PlayableSliceBlockerSwarm/1
```

at `evidence/playable_slice_blocker_swarm.json`.

## Process 1 shard

Process 1 remains the only owner allowed to publish the final outer Vehicle-root -> BMW VHF-root semantic relation and `SHIFT.BMWBody0BindFrameProof/1`.

Current work:

- consume `SHIFT.OuterVehicleRenderSnapshotAffineBridge/1`;
- consume `SHIFT.OuterVehicleRenderRootDeltaProvenance/1`;
- join exact value roots to resource-frame facts supplied by Process 3;
- prove identity or an exact fixed affine delta;
- publish any independently useful positive relation stage immediately;
- compose the final BODY0 bind proof.

## Process 2 shard

Process 2 does not perform semantic adjudication. When normal runtime work is exhausted it may:

- build/verify the strict typed consumer for the next positive outer-Vehicle/VHF relation stage;
- keep final packet/runtime admission fail-closed;
- add blocker-specific validators, packet adapters or regression tooling requested by the current P1 frontier;
- keep persistent BODY0/freshness/publication and explicit scheduler-authority regressions green;
- consume any positive stage immediately.

It must not guess the missing affine relation, manufacture candidate matrices, or set a retail admission gate positive before Process 1 proof.

## Process 3 shard

Process 3 owns the resource-side contribution to the current blocker. When normal scene/render work is exhausted it should inspect the exact canonical resource:

```text
vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

and publish a narrow resource-only contract such as:

```text
SHIFT.BMWVHFHierarchyRootResourceSemantics/1
```

The contract should freeze only facts proven by the resource itself, for example exact root node identity, matrix number, hierarchy parentage, stored local/root transform fields, and any explicit frame/resource metadata. It must clearly separate resource facts from executable ownership or dynamic-pose semantics.

Process 3 must not infer executable ownership from hierarchy shape, use visual matching as proof, or claim that a static VHF transform is the dynamic vehicle pose.

## No-idle fallback

```text
if owned runnable work exists:
    execute owned work
elif a positive handoff is available:
    consume it immediately
else:
    join current shortest blocker swarm on the assigned non-overlapping shard
```

A process may stop only if its assigned shard has no admissible task that shortens the current blocker and the coordinator has explicitly exhausted all reusable infrastructure immediately required by that blocker.

## Handoff order

```text
P3 resource facts
-> P1 semantic relation proof
-> P2 staged relation consumer
-> P1 final BODY0 bind proof
-> P2 retail transform admission/publication
-> P3 live Vulkan + camera consumers
```

This keeps all three processes active on one blocker graph without allowing multiple processes to invent competing semantic truths.
