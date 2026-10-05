# Playable Linux Slice — Process 1/2/3 Instructions v2

Status: **canonical coordination instructions**

Updated: 2026-10-05

These instructions define how Process 1, Process 2 and Process 3 coordinate work toward the first native playable Linux vertical slice. They supersede older broad process goals whenever those goals conflict with the blocker graph below.

Historical phase documents remain evidence and implementation records. They are not permission to continue a branch of work that no longer shortens the current blocker graph.

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

The project is not optimizing for complete semantic recovery of every `SHIFT.exe` function before this milestone. Work outside the path below is deferred unless it creates infrastructure required by the next unresolved edge.

## 2. Mandatory blocker question

Before every new substantial task, answer:

> **Which concrete blocker of the first playable Linux vertical slice does this work remove?**

A task is admissible only when at least one of these is true:

1. it makes a currently blocked edge positive;
2. it produces evidence required to make the next edge positive;
3. it creates reusable infrastructure immediately required by that next edge;
4. it fixes a regression that prevents an already-positive edge from executing.

If none is true, defer the task.

Do not justify work only with statements such as "useful for later", "improves coverage", "cleans up the subsystem", "more complete decompilation", or "could help eventually".

## 3. Current blocker graph

```text
PROCESS 1
BODY0 construction/bind provenance
        |
        v
positive SHIFT.BMWBody0BindFrameProof/1
        |
        v
retail outer-update scheduler/cadence ownership
        |
        +-----------------------------+
        |                             |
        v                             v
missing physics/control          frame/owner proofs
producer provenance                   |
        |                             |
        +-------------+---------------+
                      v
PROCESS 2
retail-admissible persistent BODY0 update
        |
        v
current vehicle world transform
        |
        +-------------------+
        |                   |
        v                   v
camera-follow source     PROCESS 3
and timing              Silverstone + BMW
        |               exact resources
        |               live Vulkan transform
        +---------+---------+
                  v
          PLAYABLE LINUX SLICE
```

Current shortest semantic blocker: **`SHIFT.BMWBody0BindFrameProof/1`**.

Current known construction lane that must remain the first static target:

```text
FUN_007b3670
  -> FUN_007bba90
  -> FUN_007bbb10
  -> FUN_007bbb60
```

The resolved-direct `FUN_007b7840` construction-bind branch has already been rejected. Do not spend the critical path reopening it without new independent evidence of an indirect/address-taken bind role.

## 4. Shared rules for all processes

### 4.1 Evidence before semantics

Maintain the repository's fail-closed policy:

- static executable evidence, runtime observation and native reconstruction remain separate;
- callgraph proximity is not ownership;
- a matching numeric value is not provenance;
- a native implementation is not automatically recovered retail behavior;
- ambiguous values stay ambiguous;
- runtime-owned resources are not synthesized merely to make a frame render;
- synthetic fixtures may test infrastructure but may not satisfy a retail-semantic gate.

### 4.2 Every task has four fields

Before implementation, record mentally or in the resulting phase document:

```text
BLOCKER   concrete blocked edge being shortened
INPUT     exact existing evidence/contract used
OUTPUT    exact proof/contract/runtime capability produced
CONSUMER  specific downstream Process 2/3 code or next Process 1 proof that consumes it
```

If `CONSUMER` cannot be named, the work is normally out of scope for the current milestone.

### 4.3 Prefer narrow targeted proof over broad exploration

The Ghidra evidence database already provides broad structural coverage. Prefer targeted instruction/p-code/value-provenance work on the current frontier instead of general classification of unrelated functions.

Runtime capture must also be bounded to a named unresolved value/identity/scheduling question. Do not request long traces when a short controlled observation can answer the gate.

### 4.4 Handoffs must be machine-readable

Cross-process facts should be represented by explicit versioned contracts/proofs whenever practical, for example:

```text
SHIFT.<Name>/1
```

A handoff should state:

```text
status       proven / verified / inferred / ambiguous / unknown / blocked
binary       retail identity when relevant
subject      exact function/object/resource identity
claim        narrowly stated fact
provenance   source addresses / callsites / stores / resources
limits       what is explicitly not proven
consumer     next process/path that may use the claim
```

Do not pass prose assumptions across process boundaries as if they were positive evidence.

### 4.5 Stop after the blocker is removed

When a task makes its claimed edge positive, hand the result to the downstream process. Do not continue expanding the subsystem merely because nearby work is available.

## 5. PROCESS 1 — static proof / ABI / producer / scheduling

### Mission

Process 1 exists to make semantic gates positive for executable native integration.

```text
retail executable/resources/runtime evidence
        -> exact identity / ABI / producer / ownership / scheduling proof
        -> machine-readable positive handoff
        -> Process 2 or Process 3
```

### Current priority order

Process 1 must work in this order unless new evidence changes the blocker graph:

```text
P1.1  close SHIFT.BMWBody0BindFrameProof/1
P1.2  prove retail outer-update scheduler/cadence ownership
P1.3  prove missing external vehicle-physics producers
P1.4  prove input -> drivetrain/wheel/control producer mapping
P1.5  prove retail camera-follow source and timing
P1.6  resolve exact render/resource identities only when Process 3 is blocked on them
```

### Immediate target: BODY0 bind frame

The immediate goal is exact target/value provenance from the real construction chain into the persistent `0x170` BODY record and then into BMW BODY0 identity.

Required closure:

```text
construction function
  -> exact target pointer
  -> persistent BODY record identity
  -> exact origin/basis stores or proven source values
  -> BMW chassis BODY index 0 join
  -> concrete M_BODY0_bind materialization
  -> positive SHIFT.BMWBody0BindFrameProof/1
```

Useful work includes targeted instruction export, p-code/value-flow analysis, exact caller/callee closure, store-root tracing and narrowly-scoped runtime observation when static evidence is insufficient.

### Process 1 must not

- classify unrelated functions for coverage alone;
- expand broad vtable/factory taxonomies without a named blocker consumer;
- infer object ownership from callgraph adjacency;
- treat host `1/60` pacing as retail cadence;
- fabricate provider/control semantics to unblock Process 2;
- reopen rejected proof branches without new evidence.

### Process 1 completion condition

A Process 1 task is complete when it emits a positive or correctly negative/blocked machine-readable result that changes the next decision in the blocker graph.

Negative proof is useful only when it removes a live candidate branch and identifies the next frontier.

## 6. PROCESS 2 — native physics/runtime execution

### Mission

Process 2 converts positive source-backed handoffs into continuously executing native vehicle state.

```text
positive Process 1 proof
        -> native implementation
        -> fail-closed validation
        -> persistent execution across ticks
        -> current vehicle world transform
```

Process 2 is no longer an open-ended recovered-primitive implementation program. The numerical and persistence infrastructure is already substantial. New work must connect a positive upstream handoff to the playable vehicle path.

### Current proven infrastructure

Treat the following as infrastructure, not as reasons to create adjacent speculative phases:

- native fixed-step runtime boundary;
- persistent runtime state;
- provider-absent BODY feedback execution;
- solver/reset/post-solve infrastructure;
- persistent BODY accumulator state;
- explicit BODY state generation/lineage across ticks;
- BODY0 selection/identity infrastructure;
- BODY0 -> vehicle world-matrix transport infrastructure;
- runtime handoff to live Vulkan vehicle upload.

### Current priority order

```text
P2.1  consume positive BMW BODY0 bind/frame proof
P2.2  consume retail cadence/scheduler proof
P2.3  internalize newly proven vehicle-physics producers
P2.4  connect proven control producers to drivetrain/wheel state
P2.5  execute retail-admissible persistent BODY0 pose update
P2.6  publish fresh current vehicle world transform every admitted tick
P2.7  expose the proven current transform to camera-follow integration
```

### Admission rule

Before implementing new retail semantics, Process 2 must be able to answer:

> **Which positive Process 1 handoff authorizes this value, producer, owner, transform or schedule?**

If there is no positive handoff, keep the production path closed. Synthetic values are allowed only in explicitly test-only fixtures and must remain visibly labelled as such.

### Process 2 must not

- reinterpret BODY accumulator lanes as pose without source proof;
- schedule `FUN_00770e80` merely because the native loop runs at `1/60`;
- invent missing provider outputs;
- promote prepared fixtures into retail runtime truth;
- add new physics primitives unless a current handoff needs them;
- continue solver infrastructure work after the active blocker has moved upstream.

### Process 2 completion condition

For the playable milestone, Process 2 is done when authentic retail inputs and proven producers can drive a persistent vehicle update whose BODY0 pose produces a fresh vehicle world transform across continuous ticks, without test-only motion scripts or unsupported semantic guesses.

## 7. PROCESS 3 — resources / scene / render

### Mission

Process 3 turns exact retail resources plus live runtime transforms into the visible playable frame.

```text
retail resources
  -> exact resource identity
  -> scene/material/shader contracts
  -> Silverstone + real BMW composition
  -> live vehicle/camera transforms
  -> Vulkan frame
```

The basic renderer is not the current primary blocker. Treat XCB/Vulkan bootstrap, swapchain execution, indexed multi-draw, scene-set submission and existing material/texture transport as established infrastructure.

### Current priority order

```text
P3.1  keep Silverstone + exact retail BMW composition continuously runnable
P3.2  consume Process 2 fresh vehicle world transform without test motion scripts
P3.3  consume proven camera-follow matrices/state
P3.4  resolve exact resource/shader identities only when visible slice admission is blocked
P3.5  fix renderer/runtime regressions that prevent the continuous slice
```

### Exactness rule

Continue the fail-closed resource policy:

- exact archive/resource identity outranks basename fallback;
- tied shader/resource cases remain blocked until evidence resolves them;
- renderer-owned resources are not silently synthesized;
- visual similarity is not proof of retail identity.

### Process 3 must not

- develop unrelated renderer features;
- broaden material coverage for assets outside the first slice;
- optimize rendering before correctness blocks execution;
- implement speculative post-processing/LOD/streaming features not required by the current Silverstone + BMW slice;
- compensate for missing Process 1/2 semantics with render-side animation hacks.

### Process 3 completion condition

For the playable milestone, Process 3 is done when one continuous native session loads Silverstone and the real BMW from retail resources, consumes current vehicle and camera transforms, and renders the changing result through Vulkan with no test-only transform script required for the core loop.

## 8. Cross-process handoff protocol

When a process finishes a blocker-relevant task, it must identify the next owner immediately.

```text
Process 1 proof about physics/runtime semantics -> Process 2
Process 1 proof about exact render/resource identity -> Process 3
Process 2 current vehicle transform -> Process 3 + camera integration
Process 3 resource/render failure requiring semantic identity -> Process 1
```

Do not duplicate the same uncertainty independently in multiple processes. The process that owns the evidence question resolves it once and emits a reusable contract.

## 9. Current synchronization checkpoint

As of 2026-10-05:

```text
Process 1:
  shortest blocker = SHIFT.BMWBody0BindFrameProof/1
  current frontier = construction-side persistent BODY record/value provenance

Process 2:
  continuous persistent BODY accumulator lineage is positive
  retail outer-update scheduling remains gated
  pose/world-transform production remains gated by Process 1 proofs

Process 3:
  Silverstone/native scene/Vulkan path is established
  Silverstone + real BMW composition infrastructure exists
  live retail vehicle motion is waiting on Process 2 current transform
```

This checkpoint should be updated when the blocker graph materially changes. Do not rewrite the architecture after every phase; update it when a handoff changes process ownership or removes a major edge.

## 10. Definition of playable milestone

The first playable Linux vertical slice is complete only when one session satisfies all of the following:

```text
[ ] authentic Silverstone resources are loaded
[ ] a real retail BMW vehicle is instantiated
[ ] user input reaches source-backed vehicle control producers
[ ] physics executes continuously with persistent state
[ ] BODY0 pose is current and retail-admissible
[ ] BODY0 produces the current vehicle world transform
[ ] camera follows the current vehicle source with proven timing/ownership
[ ] Vulkan renders Silverstone + BMW continuously
[ ] no test-only transform script drives core vehicle motion
[ ] no unsupported semantic guess is required for the core loop
```

Until every item is true, optimize for the shortest remaining blocker rather than subsystem completeness.
