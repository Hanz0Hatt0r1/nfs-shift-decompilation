# Playable Linux Slice — Process 1/2/3 Instructions v3

Status: **canonical coordination instructions**

Updated: 2026-10-06

These instructions define how Process 1, Process 2 and Process 3 work in parallel toward the first native playable Linux vertical slice. They supersede V2 and older broad process goals whenever those goals conflict with the blocker graph or ownership rules below.

Historical phase documents remain evidence and implementation records. They are not permission to continue work that no longer shortens the current blocker graph.

## 1. Single milestone

All three processes optimize for one chain only:

```text
Silverstone
+
real retail vehicle
+
resource-driven bootstrap
+
input
+
continuous persistent physics
+
vehicle world transform
+
camera
+
Vulkan rendering
=
native playable Linux vertical slice
```

The project is not optimizing for complete semantic recovery of every `SHIFT.exe` function before this milestone.

## 2. Mandatory blocker question

Before every substantial task, answer:

> **Which concrete blocker of the first playable Linux vertical slice does this work remove?**

A task is admissible only when it:

1. makes a currently blocked edge positive;
2. produces evidence required for the next edge;
3. creates reusable infrastructure immediately required by the next edge; or
4. fixes a regression preventing an already-positive edge from executing.

If none applies, defer it.

Every task must have:

```text
BLOCKER   concrete edge being shortened
INPUT     exact evidence/contract already available
OUTPUT    exact proof/contract/runtime capability produced
CONSUMER  exact downstream process/path that consumes it
```

If `CONSUMER` cannot be named, the task is normally out of scope.

## 3. Current blocker graph

```text
PROCESS 1
outer Vehicle-root -> exact BMW VHF vehicle-root relation
        |
        v
positive SHIFT.BMWBody0BindFrameProof/1
        |
        +------------------------------+
        |                              |
        v                              v
retail outer-update              missing physics/control
scheduler/cadence                producer provenance
        |                              |
        +---------------+--------------+
                        v
PROCESS 2
retail-admissible persistent BODY0 update
        |
        v
fresh current vehicle world transform
        |
        +-------------------+
        |                   |
        v                   v
camera-follow source     PROCESS 3
and timing              exact Silverstone + BMW
        |               live Vulkan transform
        +---------+---------+
                  v
          PLAYABLE LINUX SLICE
```

The shortest semantic blocker remains **`SHIFT.BMWBody0BindFrameProof/1`**, but its immediate sub-frontier changed on 2026-10-06.

Already positive and therefore not to be rediscovered:

```text
SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1
SHIFT.BMWVehicleRenderModelResourceJoin/1
selected BMW Vehicle Render Model = BMW_M3_E36.vhf
canonical resource = vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

The current shortest static frontier is now:

```text
BODY0-local
  -> outer Vehicle-root              [already structurally/numerically narrowed]
  -> exact BMW VHF vehicle-root      [current unresolved relation]
  -> concrete BODY0 bind composition
  -> positive SHIFT.BMWBody0BindFrameProof/1
```

The bounded evidence frontier is `SHIFT.OuterVehicleVHFRootRelationFrontier/1`, centered on `PhysicsParticipant::Restart`, `FUN_007927c0`, and its exact transform fan-out. New runtime capture/original-game execution is not required for this edge unless later static work proves that the needed value is unavailable statically.

Rejected car-body `+0x34/+0x534`, render-manager `+0xca4`, and resolved-direct `FUN_007b7840` construction-bind hypotheses must not be reopened without new independent evidence.

## 4. Parallel execution model

The three processes are deliberately **not** three independent reverse-engineering projects. They are three workers on one dependency graph.

### 4.1 Ownership

```text
PROCESS 1 owns:
  retail semantic proof
  ABI/value provenance
  owner/producer identity
  scheduler/cadence proof
  control-producer mapping
  camera-source/timing proof

PROCESS 2 owns:
  native physics/runtime implementation
  consumption of positive Process 1 contracts
  persistent execution and freshness
  fail-closed runtime admission
  publication of current vehicle transform

PROCESS 3 owns:
  exact retail resource admission
  scene/bootstrap composition
  Vulkan/render execution
  consumption of Process 2 transforms
  visible slice regressions
```

Do not duplicate an unresolved evidence question in two processes. The evidence owner resolves it once and emits a reusable machine-readable contract.

### 4.2 Parallel work rule

A downstream process does not have to idle while Process 1 works, but it may only do one of the following:

- consume already-positive handoffs;
- close an implementation gap already authorized by positive evidence;
- build the **immediate** fail-closed consumer seam required by the next expected handoff;
- fix a regression on the current slice path.

It may not guess the missing upstream semantic value in order to stay busy.

### 4.3 Conflict avoidance

Each process works on its own branch prefix:

```text
process-1/<blocker>
process-2/<consumer>
process-3/<slice>
```

Only coordination work should normally modify:

```text
PROCESS_INSTRUCTIONS.md
docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V3.md
docs/PLAYABLE_SLICE_PARALLEL_PROCESS_PROMPTS.md
```

Individual processes should update their own proof/frontier/phase documents and machine-readable evidence instead. This reduces merge conflicts between parallel workers.

Before opening or merging a PR, re-read current `main`. If another process has already removed the claimed blocker or changed the expected handoff, stop expanding the old task and retarget to the new shortest admissible edge.

### 4.4 Autonomous merge rule

Do not wait for manual confirmation after every blocker-sized change. A process may merge its own PR when all of the following are true:

- the PR has a named playable-slice blocker;
- focused tests/CI pass;
- no unresolved review/merge conflict remains;
- no fail-closed gate was promoted without evidence;
- the change does not silently overwrite another process's newer handoff.

After merge, immediately state the gate changed and the next owner.

## 5. Shared evidence rules

Maintain fail-closed semantics:

- static executable/resource evidence, runtime observation and native reconstruction remain separate;
- callgraph proximity is not ownership;
- equal numeric values are not provenance;
- visual similarity is not resource identity;
- host `1/60` pacing is not retail outer-update cadence;
- a native implementation is not automatically recovered retail behavior;
- ambiguous values stay ambiguous;
- synthetic fixtures may test infrastructure but may not satisfy a retail-semantic gate.

Cross-process handoffs should be versioned machine-readable contracts when practical:

```text
SHIFT.<Name>/1
```

Each handoff should record:

```text
status       proven / verified / inferred / ambiguous / unknown / blocked
binary       retail identity when relevant
subject      exact function/object/resource
claim        narrowly stated fact
provenance   addresses/callsites/stores/resources
limits       explicitly unproven claims
consumer     exact downstream path
```

## 6. PROCESS 1 — static proof / ABI / producer / scheduling

### Mission

```text
retail executable/resources
  -> exact identity / ABI / value / owner / scheduling proof
  -> machine-readable handoff
  -> Process 2 or Process 3
```

### Current queue

```text
P1.1  close outer Vehicle-root -> exact BMW VHF vehicle-root relation
P1.2  compose/finalize positive SHIFT.BMWBody0BindFrameProof/1
P1.3  prove retail outer-update scheduler/cadence ownership
P1.4  prove deepest missing external vehicle-physics producers
P1.5  prove input -> drivetrain/wheel/control producer mapping
P1.6  prove retail camera-follow source and timing
```

### Immediate work

Consume the already-positive BMW resource identity instead of rediscovering it. Start from `SHIFT.OuterVehicleVHFRootRelationFrontier/1` and answer the exact receiver/transform value flow through `PhysicsParticipant::Restart -> FUN_007927c0 -> fan-out`, then join only the proven owner-producing edge to the exact BMW VHF hierarchy root.

Required closure:

```text
outer Vehicle transform source
  -> exact fan-out receiver/value provenance
  -> exact BMW VHF hierarchy/root owner
  -> identity or proven fixed affine delta
  -> BODY0-local -> VHF vehicle-root numeric relation
  -> positive SHIFT.BMWBody0BindFrameProof/1
```

Do not broaden into renderer reconstruction. Do not request runtime capture unless the static frontier reaches a value that cannot be recovered from existing executable/resource evidence.

### Process 1 must not

- classify unrelated functions for coverage;
- build broad vtable/factory taxonomies without a named consumer;
- reopen rejected branches without new evidence;
- implement native runtime behavior owned by Process 2;
- compensate for missing proof with guessed semantics.

## 7. PROCESS 2 — native physics/runtime execution

### Mission

```text
positive Process 1 handoff
  -> native implementation
  -> fail-closed admission
  -> persistent execution across ticks
  -> fresh current vehicle world transform
```

### Parallel queue while P1.1/P1.2 are running

Process 2 should not redo the bind proof. In parallel it should:

```text
P2.A  audit current external-provider/frontier contracts against latest merged Process 1 proofs
P2.B  internalize the highest-priority already-positive producer/owner handoff not yet consumed
P2.C  ensure the BODY0 bind-proof consumer path fails closed and can accept the final positive contract without redesign
P2.D  ensure cadence/scheduler consumption is explicit and cannot silently fall back to host 1/60
P2.E  keep persistent BODY0 -> world-transform freshness/publication regressions green
```

If P2.A finds no positive unconsumed handoff and P2.C/P2.D infrastructure already exists, stop rather than inventing work. Wait only at the semantic gate, not by expanding unrelated solver code.

### Priority after bind proof lands

```text
P2.1  consume positive SHIFT.BMWBody0BindFrameProof/1
P2.2  materialize retail-admissible persistent BODY0 pose/world transform
P2.3  consume retail scheduler/cadence proof
P2.4  internalize proven physics/control producers
P2.5  publish a fresh current vehicle world transform every admitted tick
P2.6  expose the current transform to camera integration
```

### Process 2 must not

- infer pose from unrelated accumulator lanes;
- auto-schedule retail update from host frame rate;
- invent provider outputs;
- promote fixtures into production truth;
- add physics primitives without a current positive handoff consumer.

## 8. PROCESS 3 — resources / scene / render

### Mission

```text
exact retail resources
  -> resource-driven Silverstone + BMW scene
  -> live vehicle/camera transforms
  -> Vulkan frame
```

### Parallel queue while Process 1 closes bind semantics

The BMW render-model identity is now positive, so Process 3 can make concrete progress without guessing physics:

```text
P3.A  consume SHIFT.BMWVehicleRenderModelResourceJoin/1 in the production resource-driven bootstrap
P3.B  verify the selected BMW primary VHF is exactly vehicles/bmw_m3_e36/bmw_m3_e36.vhf, without basename fallback
P3.C  keep Silverstone + BMW Vulkan composition continuously runnable from retail resources
P3.D  verify the live transform sink accepts Process 2 freshness-gated matrices and rejects stale/test-only core motion
P3.E  fix only renderer/resource regressions that prevent this slice
```

Camera-follow semantics remain evidence-gated. Process 3 may maintain a typed camera-matrix consumer seam, but must not synthesize retail camera ownership/timing.

### Process 3 must not

- develop unrelated renderer features;
- broaden materials/assets outside the first slice;
- optimize before correctness;
- use render-side animation to hide missing Process 2 motion;
- downgrade exact resource identity to basename or visual matching.

## 9. Handoff and PR protocol

Every blocker-relevant PR body should contain:

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

Typical ownership transfer:

```text
Process 1 physics/runtime semantic proof -> Process 2
Process 1 exact render/resource proof    -> Process 3
Process 2 fresh vehicle transform        -> Process 3 + camera consumer
Process 3 semantic identity failure      -> Process 1
```

When a gate changes, downstream processes should consume the committed artifact/contract rather than re-derive the fact from prose.

## 10. Synchronization checkpoint — 2026-10-06

```text
Process 1:
  BMW Vehicle Render Model resource identity = POSITIVE
  canonical BMW VHF resource identity         = POSITIVE
  current static frontier                     = outer Vehicle-root -> BMW VHF vehicle-root
  BODY0 bind-frame proof                      = BLOCKED on that frame relation

Process 2:
  persistent native BODY infrastructure       = POSITIVE
  BODY0/world-transform transport             = READY, semantic bind gate still closed
  retail cadence                              = BLOCKED on Process 1 proof
  producer/control gaps                       = partially external/evidence-gated

Process 3:
  Silverstone scene/Vulkan path                = POSITIVE infrastructure
  exact BMW VHF identity                       = POSITIVE
  live transform sink                          = READY
  authentic moving transform                  = waiting on Process 2
  retail camera follow                         = evidence-gated
```

## 11. Definition of playable milestone

The slice is complete only when one continuous native session satisfies:

```text
[ ] authentic Silverstone resources loaded
[ ] real retail BMW instantiated from exact resources
[ ] user input reaches source-backed control producers
[ ] physics executes continuously with persistent state
[ ] BODY0 pose is current and retail-admissible
[ ] BODY0 produces the fresh vehicle world transform
[ ] camera follows the proven current vehicle source/timing
[ ] Vulkan renders Silverstone + BMW continuously
[ ] no test-only transform script drives core vehicle motion
[ ] no unsupported semantic guess is required for the core loop
```

Until all items are true, optimize for the shortest remaining blocker, not subsystem completeness.
