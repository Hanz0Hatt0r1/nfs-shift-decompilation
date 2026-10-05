# Playable Linux Slice — Process 1/2/3 Instructions v4

Status: **canonical coordination instructions**

Updated: 2026-10-06

This document supersedes v3 for coordination. Historical phase/proof documents remain evidence records, not permission to reopen closed branches.

## 1. Single milestone

All work optimizes for one chain:

```text
Silverstone
+ real retail BMW
+ resource-driven bootstrap
+ input
+ continuous persistent physics
+ fresh vehicle world transform
+ camera
+ Vulkan rendering
= native playable Linux vertical slice
```

Before every substantial task answer:

> **Which concrete blocker of the first playable Linux vertical slice does this work remove?**

Admissible work must close a blocked edge, produce evidence required by the next edge, build immediately-required reusable infrastructure, consume an already-positive handoff, or fix a regression on the current slice path.

Every task has:

```text
BLOCKER / INPUT / OUTPUT / CONSUMER
```

## 2. Current blocker graph

```text
PROCESS 1
BODY0 identity/owner                         [positive, consumed]
BODY0/VHF composition formula               [positive, consumed]
exact BMW VHF resource identity             [positive]
outer Vehicle render-snapshot affine bridge [positive]
        |
        v
outer Vehicle-root -> exact BMW VHF HIERARCHY root relation [BLOCKED]
        |
        v
numeric BODY0-local -> VHF root composition
        |
        v
positive SHIFT.BMWBody0BindFrameProof/1
        |
        +-------------------------------+
        |                               |
        v                               v
retail outer-update scheduler      physics/control producer proofs
        |                               |
        +---------------+---------------+
                        v
PROCESS 2
retail-admissible persistent BODY0 update
        |
        v
fresh current vehicle world transform
        |
        +--------------------+
        |                    |
        v                    v
camera-follow source      PROCESS 3
and timing               Silverstone + exact BMW
        |                live Vulkan transform
        +----------+---------+
                   v
            PLAYABLE LINUX SLICE
```

The shortest semantic blocker is still the exact outer Vehicle-root -> canonical BMW VHF root relation needed by `SHIFT.BMWBody0BindFrameProof/1`.

Latest static progress already merged:

```text
SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1                  positive
SHIFT.BMWVehicleRenderModelResourceJoin/1                        positive
SHIFT.OuterVehicleRenderSnapshotAffineBridge/1                   positive
FUN_00795d60 render-root delta producer/value provenance frontier bounded
canonical BMW VHF = vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

Still false:

```text
outer_vehicle_root_to_VHF_vehicle_root_ready
outer_vehicle_root_to_VHF_fixed_affine_delta_ready
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready
BODY0_bind_frame_proof_ready
vehicle_world_transform_ready
```

Rejected car-body `+0x34/+0x534`, render-manager `+0xca4`, and resolved-direct `FUN_007b7840` construction-bind hypotheses remain closed unless new independent evidence appears.

## 3. New rule: staged cross-process handoffs

A downstream process must **not** wait for a large final proof if positive sub-contracts already exist.

Process 1 publishes every independently useful positive stage as soon as it is proven. Process 2 consumes each positive stage immediately, while the final semantic admission remains fail-closed.

Canonical Process 2 staging contract:

```text
SHIFT.Process2BMWBody0BindFrameStagedHandoff/1
```

in:

```text
evidence/process2_bmw_body0_bind_frame_staged_handoff.json
```

For the BODY0 bind path the contract currently separates:

```text
retail BODY0 identity                         positive-consumed
BODY0/VHF composition formula                 positive-consumed
exact BMW VHF resource identity               positive-available
outer Vehicle render-snapshot affine bridge   positive-available
outer Vehicle -> exact VHF root relation      blocked
final SHIFT.BMWBody0BindFrameProof/1           blocked
```

Only the final retail vehicle-world-transform admission is allowed to wait for the final proof. Process 2 must not idle merely because `SHIFT.BMWBody0BindFrameProof/1` is incomplete.

Partial stages never authorize guessing the unresolved affine/frame relation. `valid`, admission, publication, and retail-world-transform gates remain false until the exact final contract is positive.

## 4. Ownership

```text
PROCESS 1 owns:
  retail semantic proof
  ABI/value provenance
  producer/owner identity
  scheduler/cadence proof
  control-producer mapping
  camera source/timing proof

PROCESS 2 owns:
  immediate consumption of positive Process 1 stages
  native physics/runtime implementation
  persistent state/freshness
  fail-closed admission
  publication of the current vehicle transform

PROCESS 3 owns:
  exact retail resource admission
  resource-driven scene/bootstrap
  Vulkan execution
  consumption of Process 2 vehicle/camera transforms
```

Never duplicate the same unresolved evidence question in multiple processes.

## 5. Shared evidence rules

Maintain fail-closed semantics:

- callgraph proximity is not ownership;
- equal values are not provenance;
- visual similarity is not resource identity;
- host `1/60` pacing is not retail cadence;
- native reconstruction is not automatically recovered retail behavior;
- fixtures cannot satisfy retail-semantic gates;
- ambiguous values remain ambiguous;
- partial handoffs cannot be promoted into a final semantic proof.

Machine-readable handoffs should be versioned as `SHIFT.<Name>/1` and record status, subject, claim, provenance, limits, and exact consumer.

## 6. Process 1 current queue

```text
P1.1 close FUN_00795d60-produced outerVehicle delta -> exact BMW VHF HIERARCHY root semantics
P1.2 publish the exact outer Vehicle-root -> BMW VHF root relation immediately when positive
P1.3 compose/finalize positive SHIFT.BMWBody0BindFrameProof/1
P1.4 prove retail outer-update scheduler/cadence ownership
P1.5 prove deepest missing external vehicle-physics producers
P1.6 prove input -> drivetrain/wheel/control producer mapping
P1.7 prove retail camera-follow source/timing
```

P1 must publish P1.2 independently instead of withholding it until P1.3 is complete. That allows P2 to update typed consumers/frontiers without waiting for the final packet.

Do not broaden P1.1 into generic renderer reconstruction. No new runtime capture is requested unless static work proves a required value cannot be recovered from existing executable/resource evidence.

## 7. Process 2 current queue

Process 2 reads `SHIFT.Process2BMWBody0BindFrameStagedHandoff/1` before deciding it is blocked.

While P1.1-P1.3 run:

```text
P2.A consume every newly-positive bind-path stage immediately
P2.B audit/currentize external-provider contracts against latest Process 1 proofs
P2.C internalize highest-priority already-positive producer/owner handoff on the current vehicle chain
P2.D keep the final BODY0 bind packet/runtime admission seam fail-closed and ready
P2.E keep SHIFT.Process2RuntimeSchedulerAuthority/1 explicit; no host 1/60 retail fallback
P2.F keep BODY0 selection -> persistent state -> freshness -> world-transform publication -> Vulkan handoff green
```

The rule is now:

```text
missing final bind proof != Process 2 globally idle
```

If no new bind stage is available, Process 2 moves to another already-positive producer/control handoff on the current vehicle path. It must not invent new solver infrastructure merely to stay busy.

When the final proof lands:

```text
consume SHIFT.BMWBody0BindFrameProof/1
-> admit exact packet
-> compose retail-admissible BODY0 world transform
-> consume retail scheduler/cadence proof
-> execute proven physics/control producers
-> publish a fresh transform every admitted tick
-> expose it to camera/render
```

## 8. Process 3 current queue

Process 3 remains parallel and exact-resource-driven:

```text
P3.A consume SHIFT.BMWVehicleRenderModelResourceJoin/1 in production bootstrap
P3.B require exact vehicles/bmw_m3_e36/bmw_m3_e36.vhf, no basename fallback
P3.C keep Silverstone + BMW Vulkan path continuously runnable from retail resources
P3.D consume freshness-gated Process 2 matrices and reject stale/test-only core motion
P3.E fix only resource/render regressions blocking this slice
```

Camera semantics remain Process 1 evidence -> Process 2 runtime -> Process 3 consumer; render-side animation must not hide missing physics motion.

## 9. Merge and synchronization rules

Branches:

```text
process-1/<blocker>
process-2/<consumer>
process-3/<slice>
```

Coordinator-owned files include `PROCESS_INSTRUCTIONS.md` and canonical process/prompt documents.

Before opening or merging a PR, re-read current `main`. A blocker-relevant PR may be self-merged when focused tests/CI pass, no unresolved conflict exists, no unsupported gate is promoted, and no newer handoff is overwritten.

PR body:

```text
BLOCKER:
INPUT:
OUTPUT:
CONSUMER:
GATES_CHANGED:
LIMITS:
TESTS:
NEXT_OWNER:
```

After every merged cross-process handoff, downstream processes re-read `main` and retarget immediately.

## 10. Synchronization checkpoint — 2026-10-06

```text
Process 1:
  exact BMW VHF identity                         POSITIVE
  outer render-snapshot affine bridge            POSITIVE
  current static frontier                        FUN_00795d60 delta -> canonical VHF root semantics
  exact outer Vehicle -> VHF root relation       BLOCKED
  BODY0 bind-frame proof                         BLOCKED

Process 2:
  persistent BODY infrastructure                 POSITIVE
  retail BODY0 identity consumption              POSITIVE
  BODY0/VHF composition seam                     READY
  staged bind handoff policy                     READY
  final bind packet/runtime admission seam       READY, FAIL-CLOSED
  scheduler authority seam                       READY, FAIL-CLOSED
  retail cadence                                 BLOCKED on Process 1
  producer/control frontier                      ACTIVE independently of final bind proof

Process 3:
  Silverstone scene/Vulkan infrastructure        POSITIVE
  exact BMW VHF identity                         POSITIVE
  live freshness-gated transform sink            READY
  authentic moving transform                    waiting on Process 2 final admission
  retail camera follow                           evidence-gated
```

## 11. Playable definition

The milestone is complete only when one continuous native session has authentic Silverstone resources, exact BMW resources, input reaching source-backed controls, persistent admitted physics, current BODY0/world transform, proven camera source/timing, continuous Vulkan rendering, no test-only core motion, and no unsupported semantic guess.
