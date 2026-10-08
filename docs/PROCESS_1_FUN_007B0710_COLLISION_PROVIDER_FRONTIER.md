# Process 1 — `FUN_007b0710` collision-provider frontier

## BLOCKER

P1.2a still blocks Process 2 P2.4 from faithfully replacing the residual `FUN_00765c40` provider. The caller-visible collision-query ABI is already recovered, but the retail object/call that actually performs the world/scene lookup is not.

Without a narrower current contract, future work can waste time re-proving the seven-double query record, 0x58-byte cache record, selected BMW world position/cache/fallback, or hit/miss projection. Those are not the missing semantics.

## INPUT

This slice introduces no new source or machine claim. It joins existing PC-retail evidence:

- `SHIFT.CollisionQueryRuntime/1` / Phase 370: `FUN_00765c40` caller line 759173, `FUN_007b0710` source line 811231, known lower fallback-query function `FUN_0074f560`, cache record layout and observable hit/miss behavior;
- `SHIFT.NativeCollisionQueryContract/1` / Phase 666: the same caller-visible boundary in native typed form, explicitly not a collision-engine implementation;
- `SHIFT.Fun00765c40SelectedBMWWorldPosition/1`;
- `SHIFT.Fun00765c40QueryCacheLifetime/1`;
- `SHIFT.Fun00765c40SelectedBMWQueryFallback/1`;
- `SHIFT.Fun00765c40CollisionOutputHandoff/1`.

PC retail remains authoritative.

## OUTPUT

Adds `SHIFT.Fun007b0710CollisionProviderFrontier/1`.

The proof boundary is now explicit:

```text
FUN_00765c40 @ source line 759173
  -> FUN_007b0710 @ source line 811231
       caller-visible query/cache ABI        CLOSED
       hit/miss observable projection         CLOSED
       selected BMW query inputs              CLOSED
       known lower fallback-query surface     FUN_0074f560
       exact scene-query implementation       OPEN
       provider object/pointer domain          OPEN
```

The already-closed ABI remains:

```text
query record: 7 doubles
+0x00 position
+0x18 Y tolerance
+0x20 max auxiliary value
+0x28 returned contact height
+0x30 previous/returned cache handle

returned cache record: 0x58 bytes
observable hit: handle + normal + contact height
observable miss: null handle + normal (0,1,0) + no contact height
```

This contract does **not** claim that `FUN_0074f560` itself is the final provider implementation or assign it a physical PhysX class. It only records that existing PC evidence already names it as the lower fallback-query surface, so the next static review should start there rather than reopening the upper ABI.

## Remaining P1.2a proof

The next positive contract must recover, at or below `FUN_0074f560` / the scene-query boundary:

1. the object/pointer domain used for provider execution;
2. the exact direct/indirect call or virtual slot that performs the retail scene lookup;
3. the cache-reuse versus fallback-query control flow relevant to provider execution;
4. provenance from that lookup to the already-closed 0x58-byte returned surface-record boundary.

If the implementation cannot yet be internalized, Process 1 may instead publish a narrower explicit typed provider boundary, but it may not substitute a guessed track-raycast implementation.

## CONSUMER

Process 2 P2.4 may continue to consume `CollisionQueryOutput` and the selected query inputs, but must not claim the collision provider native or remove complete `FUN_00765c40` from this contract alone.

## GATES_CHANGED

- `FUN_007b0710` caller-visible contract: **closed**;
- known lower fallback-query surface `FUN_0074f560`: **pinned from existing evidence**;
- exact scene-query implementation: **open**;
- collision-provider object ownership: **open**;
- guessed native track query allowed: **false**;
- P1.2a complete: **false**.

## LIMITS

No new class names, object identities, virtual slots, source lines, or machine spans are invented. `FUN_0074f560` is not promoted beyond the role already established by Phase 370/666 evidence.

## TESTS

`tests/test_process1_fun_007b0710_collision_provider_frontier.py` cross-checks this frontier against `SHIFT.CollisionQueryRuntime/1`, the native collision-query contract surface, and the selected-session input/handoff contracts.

## NEXT_OWNER

Process 1.

## NEXT_STEP

Run a targeted PC static analysis beginning at `FUN_0074f560` and its lower scene-query calls/indirect dispatches, preserving pointer provenance until the actual provider object/call is positively identified.
