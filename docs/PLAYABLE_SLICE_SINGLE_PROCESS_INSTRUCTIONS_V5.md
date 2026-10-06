# Playable Linux Slice — Single Process Instructions v5

Status: **canonical coordination instructions**

Updated: 2026-10-06

This document supersedes the v4 three-process coordination model, blocker-swarm model, and parallel-process prompts. Historical files and contract names containing `Process1`, `Process2`, `Process3`, `process1`, `process2`, or `process3` remain evidence/ABI identifiers only; they do not define active ownership or require multiple workers.

## 1. Single milestone

All work optimizes one chain:

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

> **Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

A task is admissible only when it:

1. closes the current shortest blocked edge;
2. produces exact evidence required by that edge;
3. implements the immediate consumer of an already-positive proof;
4. builds reusable infrastructure immediately required by the next blocked edge; or
5. fixes a regression preventing an already-positive slice path from executing.

Every task must state:

```text
BLOCKER
INPUT
OUTPUT
CONSUMER
GATES_CHANGED
LIMITS
TESTS
NEXT_STEP
```

There is one active process and one owner. `NEXT_STEP` replaces cross-process `NEXT_OWNER` routing.

## 2. Execution model

There are no active Process 1 / Process 2 / Process 3 workers.

The single process owns the whole critical path:

```text
static proof / ABI / value provenance / scheduling
        |
        v
native physics/runtime execution
        |
        v
persistent vehicle + fresh world transform
        |
        v
resources / scene / camera / Vulkan integration
        |
        v
playable Linux slice
```

Do not create waiting handoffs between subsystems. A positive proof is consumed immediately in the same execution stream. Machine-readable contracts remain useful as fail-closed checkpoints and regression boundaries, but they are internal checkpoints rather than worker-to-worker messages.

The process may edit static-analysis, native-runtime, resource, scene, and renderer files in the same blocker-sized PR when that is the shortest safe way to close one edge.

## 3. Current state after PR #1331

Already positive and not to be rediscovered:

```text
retail BMW chassis BODY 0 identity
BODY0 resource/local -> SDF bind facts
selected-session BODY0 -> outer Vehicle numeric relation
SHIFT.BMWBody0VHFBindFrameFrontier/1 composition formula
SHIFT.BMWVehicleRenderModelResourceJoin/1
SHIFT.BMWVHFHierarchyRootFrame/1
SHIFT.OuterVehicleRenderSnapshotAffineBridge/1
SHIFT.OuterVehicleRenderRootDeltaProvenance/1
SHIFT.VehicleRenderModelRootAffineDomainJoin/1
SHIFT.OuterVehicleBMWVHFRootRelation/1
SHIFT.BMWVHFRootFrameSceneConsumer/1
persistent BODY/runtime transport and freshness infrastructure
live Vulkan vehicle transform sink
strict outer Vehicle/VHF relation admission infrastructure
final BODY0 bind proof packet/runtime admission seam
explicit runtime scheduler-authority seam
```

`SHIFT.OuterVehicleBMWVHFRootRelation/1` proves a setup-fixed affine semantic relation. It does **not** yet provide the selected BMW session's finite relation matrix because the three `Vehicle::InitVehicle` setup delta scalars have not yet been materialized with exact provenance.

Current false gates:

```text
outer_vehicle_root_to_VHF_relation_numeric_matrix_ready = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready    = false
BODY0_bind_frame_proof_ready                            = false
vehicle_world_transform_ready                           = false
retail_cadence_admitted                                 = false
retail_control_chain_complete                           = false
retail_camera_follow_ready                              = false
```

Rejected branches remain closed without new independent evidence:

```text
car-body +0x34/+0x534
render-manager +0xca4
resolved-direct FUN_007b7840 construction-bind hypothesis
```

## 4. Current shortest blocker

The critical path is now:

```text
SHIFT.OuterVehicleBMWVHFRootRelation/1            [POSITIVE semantic relation]
        |
        v
materialize selected BMW InitVehicle delta_local
outerVehicle +0x19c / +0x1a0 / +0x1a4             [CURRENT BLOCKER]
        |
        v
finite M_outer_to_vhf_root
        |
        v
compose already-positive BODY0 -> outer relation
        |
        v
SHIFT.BMWBody0BindFrameProof/1
        |
        v
admit persistent retail BODY0 world transform
```

The exact formulas already proven under the D3D row-vector convention are:

```text
M_vhf_root_to_outer = M_vhf_root_to_model * T(delta_local)
M_outer_to_vhf_root = inverse(M_vhf_root_to_model * T(delta_local))
```

where:

```text
delta_local = outerVehicle[+0x19c,+0x1a0,+0x1a4]
producer    = FUN_00795d60
lifetime    = Vehicle::InitVehicle/setup state
```

The immediate task is numeric materialization from exact setup inputs, not another semantic identity-vs-affine proof.

## 5. Single sequential queue

Execute this queue in order unless a newly merged proof removes or reorders a dependency:

```text
S1  materialize exact selected-BMW FUN_00795d60 delta_local values from Vehicle::InitVehicle inputs
S2  evaluate and prove finite M_outer_to_vhf_root with provenance
S3  compose BODY0 -> outer with outer -> VHF and publish positive SHIFT.BMWBody0BindFrameProof/1
S4  bind/consume the exact proof in existing native admission seams and publish fresh persistent BMW world transform
S5  prove and consume retail outer-update scheduler/cadence ownership
S6  close deepest missing vehicle-physics/control producers
S7  close input -> drivetrain/wheel/control mapping and execute it continuously
S8  prove/consume retail camera-follow source and timing
S9  run the exact Silverstone + BMW resource-driven Vulkan session with no test-only core motion
```

Do not start S5-S9 merely because S1-S4 are difficult. Work may temporarily move to an immediately adjacent consumer seam only when it directly reduces latency for the current blocker and cannot promote an unsupported gate.

## 6. Internal checkpoint rule

Keep existing versioned contracts such as `SHIFT.<Name>/1` and historical `Process1/2/3`-named formats stable when they are already consumed by code/tests.

Their active interpretation is:

```text
proof/checkpoint becomes positive
-> same process consumes it immediately
-> next gate remains fail-closed until its own requirements are positive
```

Do not rename stable contracts merely to remove historical process labels. Renaming them would create compatibility work without shortening the playable-slice blocker graph.

New coordination contracts should use neutral names. The canonical execution contract is:

```text
SHIFT.PlayableSliceSingleProcessExecution/1
```

in `evidence/playable_slice_single_process_execution.json`.

## 7. Evidence and fail-closed rules

Maintain these invariants:

- callgraph proximity is not ownership;
- equal numeric values are not provenance;
- visual similarity is not resource identity;
- identity-valued matrices do not prove identity semantics;
- host `1/60` pacing is not retail scheduler/cadence evidence;
- native reconstruction is not automatically recovered retail behavior;
- fixtures/test scripts cannot satisfy a retail-semantic gate;
- ambiguous values remain ambiguous;
- static VHF object transforms are not dynamic vehicle pose;
- no render-side animation may hide absent physics motion.

No new runtime capture/original-game execution is requested while the required value can still be recovered from existing executable/resource evidence. If static work proves a required runtime-only value is unavailable, request the narrowest capture/probe that answers that exact value question.

## 8. Work selection when blocked

There is no blocker swarm and no secondary worker to wait for.

Use this decision rule:

```text
if current shortest blocker has an admissible proof/implementation step:
    do it
elif its immediate consumer seam is missing and can be built fail-closed:
    build that seam
elif a required reusable analyzer/validator is missing:
    build only that blocker-specific tool
else:
    produce a narrower fail-closed frontier identifying the exact missing value/evidence
```

Do not broaden into unrelated solver, renderer, resource, taxonomy, coverage, optimization, or cleanup work merely to stay busy.

## 9. Branch / PR / merge protocol

Use one branch namespace:

```text
slice/<blocker>
```

Legacy `process-1/`, `process-2/`, and `process-3/` branches may remain in history but are not the active convention.

Before opening or merging a blocker-relevant PR, re-read current `main`. If another merge already closed or changed the blocker, retarget immediately.

PR body:

```text
BLOCKER:
INPUT:
OUTPUT:
CONSUMER:
GATES_CHANGED:
LIMITS:
TESTS:
NEXT_STEP:
```

A PR may be self-merged when:

- it names the current playable-slice blocker;
- focused tests and required CI pass;
- no unresolved conflict/review blocker exists;
- no fail-closed gate is promoted without evidence;
- it does not overwrite a newer proof/consumer state.

After merge, re-read `main`, state the changed gates, and continue with the next shortest edge.

## 10. Current integration inventory

The single process must preserve these already-built paths while closing remaining semantics:

```text
resources:
  exact BMW primary VHF identity and root frame
  Silverstone resource-driven bootstrap

physics/runtime:
  persistent BODY state
  retail BODY0 identity/selection
  BODY0 pose transport
  fixed composition formula
  proof packet/runtime admission seams
  generation/freshness checks
  explicit scheduler authority boundary

render:
  exact BMW root-frame preservation into production scene path
  live freshness-gated Vulkan vehicle upload
  Silverstone + BMW Vulkan composition
```

These are consumers/infrastructure, not permission to claim missing retail semantics.

## 11. Playable completion definition

The milestone is complete only when one continuous native Linux session satisfies all of:

```text
[ ] authentic Silverstone resources loaded
[ ] exact retail BMW instantiated from canonical resources
[ ] input reaches source-backed retail control producers
[ ] physics executes continuously with persistent state
[ ] BODY0 pose is current and retail-admissible
[ ] BODY0 produces a fresh current vehicle world transform
[ ] retail update cadence/scheduler authority is proven and consumed
[ ] camera follows the proven current vehicle source/timing
[ ] Vulkan continuously renders Silverstone + moving BMW
[ ] no test-only transform script drives core vehicle motion
[ ] no unsupported semantic guess is required by the core loop
```

Until then, optimize the one process for the shortest remaining blocker, not subsystem completeness.