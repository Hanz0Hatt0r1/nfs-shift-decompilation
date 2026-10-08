# SHIFT Decompilation Roadmap

This roadmap describes **execution strategy**, not the volatile live frontier.

Live phase, provider count, queue state, blocker burndown and parallel-ready work are generated from the canonical execution state:

- [`coordination/PLAYABLE_SLICE_STATUS.md`](coordination/PLAYABLE_SLICE_STATUS.md)
- [`evidence/playable_slice_three_process_execution.json`](evidence/playable_slice_three_process_execution.json)

Detailed historical reconstruction work remains preserved in `docs/PHASE*.md`. Historical phase documents are evidence/history and must not be used to select new work.

## Current milestone

The first target is a native Linux/Vulkan playable vertical slice:

```text
Silverstone
+
exact retail BMW M3 E36 resources
+
resource-driven bootstrap
+
continuous persistent physics
+
retail-backed input/control
+
fresh vehicle world transform
+
retail-backed camera follow
+
Vulkan presentation
=
native playable Linux vertical slice
```

The project does not require every `SHIFT.exe` function to be reconstructed before this milestone. Work is selected by whether it removes a current blocker, supplies evidence required by the next dependency edge, or creates infrastructure immediately reusable by that edge.

## Execution order

### 1. Retail proof lanes

`P1A-contact`, `P1B-control` and `P1D-camera` run independently where possible.

They own:

- exact PC-retail ABI/value/producer provenance;
- contact/collision residual ownership;
- input -> drivetrain/wheel/control provenance;
- camera target/source/timing provenance;
- fail-closed negative proofs that permanently remove false candidates.

They hand off only explicit versioned proof/value/timing contracts.

### 2. Native runtime lane

`P2-runtime` consumes only positive retail contracts.

Priority rules:

- internalize complete boundaries in exact retail order;
- preserve typed external seams when semantics are not yet closed;
- reduce provider count only when a complete callback boundary is actually removed;
- advance independent ready work while another P2 task is blocked instead of idling the lane.

### 3. Visible integration lane

`P3-integration` owns:

- exact retail resource/bootstrap provenance;
- Silverstone/BMW scene composition;
- participant and transform handoff;
- Vulkan rendering;
- final fail-closed continuous smoke execution.

P3 may keep integration infrastructure healthy while upstream semantics remain blocked, but must not substitute guessed motion/control/camera behavior for unresolved retail gates.

## Primary readiness metrics

Phase number is not the readiness metric.

Track these values from the canonical status page:

- active external vehicle-provider count;
- complete/incomplete state of the current contact-response proof;
- retail control-chain readiness;
- retail camera-follow readiness;
- final playable-smoke runnability;
- playable-slice completion.

The architectural provider count changes only when the full externally required behavior of a boundary has been proven and consumed internally.

## Work-selection rule

Before substantial work, answer:

> **Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

If the answer is unclear, the task should normally be deferred.

Before starting and before merge:

1. re-read fresh `main`;
2. read `coordination/PLAYABLE_SLICE_STATUS.md`;
3. respect lane ownership in `coordination/lane_ownership.json`;
4. do not rediscover already-closed proof surfaces;
5. preserve newer coordination/proof state when rebasing or transplanting work.

## PR strategy

One canonical PR should own one exact blocker surface, with at most one stacked successor.

Exact negative proofs are useful progress when they permanently shrink the search space and are regression-tested.

When a stronger PR supersedes another:

1. preserve/transplant unique evidence;
2. mark the old PR superseded;
3. close it;
4. continue from fresh `main`.

Required PR fields and merge rules are defined in [`coordination/DEVELOPMENT_PROCESS_V2.md`](coordination/DEVELOPMENT_PROCESS_V2.md).

## CI strategy

Do not create another workflow for every phase.

Prefer stable workflow families plus:

- pytest targets/markers;
- CTest targets;
- data-driven workflow matrices;
- reusable subsystem gates.

Historical phase-numbered workflows are migration debt. They may be consolidated only when old/new coverage parity is demonstrated; reducing YAML count must never weaken evidence, native, capture, Vulkan or smoke gates.

## Research-input reproducibility

Large retail binaries, decompiler exports and machine-generated navigation databases remain outside Git.

Known authoritative input hashes and non-authoritative storage hints are recorded in:

- [`coordination/research_inputs.lock.json`](coordination/research_inputs.lock.json)

Rules:

- PC retail machine evidence adjudicates semantic claims;
- an unknown hash is never invented;
- generated Ghidra/SQLite navigation data does not become semantic authority by filename or location;
- Google Drive IDs are storage/discovery hints only.

## Historical roadmap

The previous long phase-by-phase roadmap mixed live execution state with historical narrative and repeatedly drifted behind `main`. Its durable evidence is already preserved in the phase documents and evidence contracts under `docs/` and `evidence/`.

Use those files to understand how a result was established; use the canonical status page to decide what should be done next.
