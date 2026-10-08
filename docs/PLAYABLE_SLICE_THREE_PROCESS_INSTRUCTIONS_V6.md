# Playable Linux Slice — Three-Process Instructions v6

Status: **canonical coordination instructions**

Updated: 2026-10-08

This document re-establishes three active, non-overlapping development lanes for the first playable Linux vertical slice. It supersedes the v5 single-process coordination model while preserving all v5 proof artifacts as historical evidence.

## 1. Milestone

All three processes optimize one shared milestone:

```text
Silverstone
+ exact retail BMW M3 E36
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

Every task must identify:

```text
BLOCKER
INPUT
OUTPUT
CONSUMER
GATES_CHANGED
LIMITS
TESTS
NEXT_OWNER
NEXT_STEP
```

## 2. Current shared frontier

Current merged main frontier is **Phase 749**.

Already positive and not to be rediscovered:

```text
retail BMW chassis BODY0 identity
BMW BODY0 bind frame
fresh persistent BMW world transform
retail outer scheduler/cadence
selected-session PhysicsTweaker rate = 180 Hz
selected-session inner substep = 1/180 s
normal outer update = 6 recovered inner substeps
FUN_007682c0 BODY0 delta/effect path substantially internalized
FUN_00765c40 selected world position/cache/fallback inputs internalized
Phase744 typed selected CollisionQueryOutput + query-scalar handoff
Phase745 same-pass selected FUN_00766510 session handoff
Phase746 primary FUN_00766510 caller accumulator delta
Phase747 shared FUN_00766510 reference-vector ownership/transform
Phase748 FUN_00713630 dynamic reference-source arithmetic/cadence
Phase749 native later +0x3a28/+0x3a40 response-state branch
Phase742 primary FUN_00766510 response application
Phase743 selected BMW application-point ownership
Process 1 response-config ownership for +0x3908/+0x3910/+0x3918/+0x3950
Process 1 earlier +0x3b20 response-branch ownership
Process 1 optional +0x3bc8/+0x3cxx response-branch ownership
Process 1 later +0x3a28/+0x3a40 response-branch ownership
Process 1 direct FUN_00753650 caller-accumulator surface (4/4)
```

The active top-level external vehicle-provider count is **7**. Do not reduce that number until an entire callback boundary can be removed without dropping source-visible behavior.

## 3. Process ownership

### PROCESS 1 — retail proof / ABI / producer / timing

Owns facts that must be proven from PC retail executable/resource evidence before native code may claim them.

Primary responsibilities:

- source/value/owner provenance;
- function ABI and call ordering;
- residual `FUN_00766510` producer/state/diagnostic ownership;
- collision-provider identity and residual `FUN_00765c40` side effects;
- input -> drivetrain/wheel/control producer mapping;
- Controller #1 scheduling/wake/message provenance where it constrains control timing;
- retail camera-follow source/timing;
- targeted Ghidra/static analyzers and evidence contracts.

Process 1 must **not** implement speculative native behavior to keep moving. It emits narrow positive contracts or a narrower fail-closed frontier.

Current queue:

```text
P1.1  close the reduced FUN_00766510 proof frontier described by
      SHIFT.Fun00766510ResidualOwnershipFrontier/1:
      a) close remaining upstream runtime inputs behind merged Phase748 FUN_00713630;
      c) source-lock exact FUN_00758fc0 caller scheduling, final transformed-vector
         accumulation, and residual conditional state/diagnostic writes
      CLOSED: later +0x3a28/+0x3a40 direct block owner/config/source order
      CLOSED: all four direct FUN_00753650 caller-accumulator sites

P1.2  identify/prove collision-provider object/call below FUN_007b0710,
      four wheel +0x738 load-term ownership, and residual FUN_00765c40 side effects

P1.3  finish input -> drivetrain/wheel/control producer provenance and
      Controller #1 timing/wake constraints required by that chain

P1.4  prove retail camera-follow source and update timing against the admitted
      current vehicle transform
```

The response-config block, earlier `+0x3b20` branch, optional `+0x3bc8/+0x3cxx` branch, later `+0x3a28/+0x3a40` branch, and `SHIFT.Fun00766510DirectCallerAccumulatorSurface/1` are already positive inputs to P1.1 and must not be re-selected as new work.

PC retail is authoritative. Xbox 360 recompilation may accelerate navigation or corroborate structure, but cannot replace PC proof.

### PROCESS 2 — native physics / runtime execution

Owns implementation and runtime consumption of positive Process 1 contracts.

Primary responsibilities:

- persistent BMW BODY execution;
- native contact/collision response integration;
- provider-boundary reduction;
- fixed-step/session orchestration;
- exact recovered arithmetic/precision behavior;
- continuous source-backed control consumption;
- fresh vehicle-transform publication.

Current queue:

```text
P2.1  COMPLETE — Phase745 same-pass FUN_00766510 selected-session handoff

P2.2  COMPLETE — Phase746 primary FUN_00766510 caller-accumulator delta
      with exact FUN_00753650 cross-product/store behavior

P2.3  CURRENT/BLOCKED ON P1.1 — preserve merged Phase747 shared-reference,
      Phase748 FUN_00713630 reference-source producer and Phase749 later-response
      native branch; consume the remaining P1.1 handoff and internalize the
      complete required FUN_00766510/contact_response behavior; target 7 -> 6

P2.4  consume P1.2 collision/load-term proofs and narrow/remove residual
      FUN_00765c40 without inventing collision semantics

P2.5  continue replacing remaining providers in dependency order:
      wheel_update -> FUN_007675f0 caller inputs -> FUN_007afdd0 scalar factory
      -> FUN_00765470 half-step refresh -> FUN_007b8810 post-half-step

P2.6  consume the proven P1.3 control chain continuously while preserving
      persistent BODY state and fresh world-transform publication
```

Process 2 may build an immediate fail-closed consumer seam for an expected P1 handoff, but may not guess the missing semantic value.

### PROCESS 3 — resources / scene / renderer / playable bootstrap

Owns the exact retail resource path and end-to-end visible Linux slice integration.

Primary responsibilities:

- BFF/resource pipeline;
- exact Silverstone + BMW scene composition;
- participant/resource handoff;
- Vulkan scene execution;
- playable profile/launcher/bootstrap;
- consumption of fresh P2 vehicle transforms;
- camera/Vulkan integration after P1/P2 handoff;
- end-to-end smoke/regression paths.

Current queue:

```text
P3.1  land/maintain the provenance-gated resource-pipeline -> playable-scene join
      (PR #1431 lineage)
P3.2  land/maintain playable pipeline launcher + profile preparation
      (PR #1442/#1443 lineage)
P3.3  land/maintain one-command playable resource-pipeline bootstrap
      (PR #1444 lineage)
P3.4  preserve exact Silverstone + BMW resource identity and participant authority
P3.5  consume P2 fresh vehicle transform and later P1.4/P2 camera handoff
P3.6  add final resource-driven Silverstone + BMW continuous smoke path
```

Process 3 must not hide missing P1/P2 semantics with render-side animation or test scripts.

## 4. Cross-process handoffs

Only explicit contracts may cross ownership lanes.

```text
PROCESS 1 proof/value/timing contract
        -> PROCESS 2 fail-closed native consumer

PROCESS 2 fresh runtime state / transform / camera feed
        -> PROCESS 3 scene/renderer/launcher consumer

PROCESS 3 resource identity/bootstrap evidence
        -> PROCESS 1/2 only when exact resource provenance is required
```

A process may continue on independent work in its own queue while another process is blocked. It may not take over another process's unresolved semantic ownership just to avoid waiting.

Every handoff must state `NEXT_OWNER` and the exact consumer path.

## 5. Conflict-avoidance rules

To keep three concurrent workers mergeable:

- Process 1 primarily edits `tools/ghidra/`, `src/physics/` proof/analyzer files, `evidence/`, and focused docs/tests.
- Process 2 primarily edits `native_runtime/`, native physics tests, and runtime-facing evidence/docs.
- Process 3 primarily edits resource/scene/render/bootstrap tooling, `native_vulkan/`, renderer tests, and integration docs.
- Avoid editing root coordination files from ordinary blocker PRs; coordination-only refreshes are allowed when merged frontier facts are stale.
- Re-read `main` before starting and again before merging.
- Retarget stacked PRs immediately when their base lands.
- Do not overwrite newer evidence generated by another process.

Active branch prefixes:

```text
process-1/<blocker>
process-2/<blocker>
process-3/<blocker>
```

Existing `slice/...` branches remain valid historical/stacked work and may finish normally.

## 6. Provider-count rule

The current metric is:

```text
active_external_provider_count = 7
```

Current boundaries:

```text
1. FUN_00765c40 residual collision/query pass
2. FUN_00758b50 wheel update
3. FUN_00766510 residual contact response
4. FUN_007675f0 remaining caller-input provider
5. FUN_007afdd0 scalar-provider factory
6. FUN_00765470 half-step refresh provider
7. FUN_007b8810 post-half-step provider
```

A field moving native does not decrement the count. The count changes only when the complete callback boundary is no longer required in the selected production session.

The first architectural target is **7 -> 6** by removing `contact_response` after P1.1/P2.3 close every required `FUN_00766510` operation.

## 7. Evidence policy

Maintain these invariants:

- PC retail is the primary semantic authority;
- Xbox recomp may corroborate/navigation-assist but not replace PC proof;
- callgraph proximity is not ownership;
- equal numeric values are not provenance;
- visual similarity is not resource identity;
- host pacing is not retail scheduler evidence;
- fixtures/test scripts cannot satisfy retail-semantic gates;
- native reconstruction is not automatically recovered retail behavior;
- missing proof stays fail-closed;
- renderer-side motion cannot substitute for physics motion.

## 8. Merge protocol

Each process may self-merge its own PR when:

- the PR names a current queue item/blocker;
- required focused tests/CI pass;
- no conflicts remain;
- no unsupported gate is promoted;
- no newer `main` evidence is overwritten;
- cross-process output contracts name their consumer.

After merge, refresh the corresponding queue state in the machine-readable execution file when the coordination frontier materially changes.

## 9. Machine-readable coordination

Canonical execution state:

```text
evidence/playable_slice_three_process_execution.json
```

Contract:

```text
SHIFT.PlayableSliceThreeProcessExecution/1
```

The v5 single-process coordination files remain historical and must not be used to select new work.
