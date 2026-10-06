# Playable Linux slice — blocker swarm mode

## BLOCKER

The shortest current blocker is:

```text
SHIFT.OuterVehicleRenderRootDeltaProvenance/1
+
SHIFT.BMWVHFHierarchyRootFrame/1              [POSITIVE, PR #1323]
-> exact outer Vehicle-root -> BMW VHF-root relation
-> SHIFT.BMWBody0BindFrameProof/1
```

Process 1 owns the final semantic proof, but Process 2 and Process 3 must not idle when their owned queues are exhausted.

## Rule

When a downstream process has no runnable positive handoff or blocking regression, it joins the **current shortest blocker swarm** on a non-overlapping shard. The semantic owner does not change.

The resource-root extraction shard is already complete: merged PR #1323 produced positive `SHIFT.BMWVHFHierarchyRootFrame/1`. Do not redo it.

```text
PROCESS 1 proof-owner shard
exact value provenance + exact positive VHF root frame
-> final outer Vehicle/VHF relation adjudication
             |
             +----------------------------+
             |                            |
             v                            v
PROCESS 2 consumer shard          PROCESS 3 frame-consumer shard
strict relation-stage validator  exact VHF root-frame preservation
+ final fail-closed admission     through production scene/runtime
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
- consume positive `SHIFT.BMWVHFHierarchyRootFrame/1` from PR #1323;
- join exact executable value roots to the exact resource frame;
- prove identity or an exact fixed affine delta;
- publish the relation immediately when positive;
- compose the final BODY0 bind proof.

## Process 2 shard

Process 2 does not perform semantic adjudication. It must immediately consume the newly-positive `SHIFT.BMWVHFHierarchyRootFrame/1` stage in the staged bind path.

When normal runtime work is exhausted it may:

- build/verify the strict typed consumer for the next positive outer-Vehicle/VHF relation stage;
- validate exact VHF root-frame identity/matrix metadata without claiming the unresolved outer relation;
- keep final packet/runtime admission fail-closed;
- add blocker-specific validators, packet adapters or regression tooling requested by the current P1 frontier;
- keep persistent BODY0/freshness/publication and explicit scheduler-authority regressions green;
- consume any positive stage immediately.

It must not guess the missing affine relation, manufacture candidate matrices, or set a retail admission gate positive before Process 1 proof.

## Process 3 shard

The old resource-root extraction task is complete and must not be repeated.

Process 3 now consumes `SHIFT.BMWVHFHierarchyRootFrame/1` in the production BMW scene path and proves that the exact canonical root frame is preserved through the existing resource/runtime chain:

```text
canonical BMW VHF
-> VHF parser / hierarchy matrix resolution
-> scene/bootstrap transform representation
-> runtime/Vulkan vehicle object frame
```

The preferred machine-readable output is:

```text
SHIFT.BMWVHFRootFrameSceneConsumer/1
```

or a narrower blocker-specific contract if one boundary remains ambiguous.

This work may prove exact frame transport and representation compatibility. It must not infer executable ownership, claim the static VHF frame is the dynamic vehicle pose, or publish the outer Vehicle/VHF semantic relation.

If this scene-frame consumer is already fully positive, Process 3 next assists only on resource-backed terminal roots explicitly exposed by the current Process 1 value slice. It must not invent a broad resource audit.

## No-idle fallback

```text
if owned runnable work exists:
    execute owned work
elif a positive handoff is available:
    consume it immediately
else:
    join current shortest blocker swarm on the assigned non-overlapping shard
```

After every upstream merge, first check whether the assigned shard was superseded. If so, retarget immediately rather than completing obsolete work.

A process may stop only if its assigned shard has no admissible task that shortens the current blocker and the coordinator has explicitly exhausted all reusable infrastructure immediately required by that blocker.

## Handoff order

```text
SHIFT.BMWVHFHierarchyRootFrame/1
-> P2 strict relation-stage validator
-> P3 exact production scene-frame consumer

P1 executable/value provenance + root-frame join
-> exact outer Vehicle/VHF relation
-> P2 staged consumer
-> P1 final BODY0 bind proof
-> P2 retail transform admission/publication
-> P3 live Vulkan + camera consumers
```

This keeps all three processes active on one blocker graph without allowing multiple processes to invent competing semantic truths.
