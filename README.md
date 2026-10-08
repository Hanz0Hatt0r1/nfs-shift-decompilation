# Need for Speed: SHIFT — decompilation and native Linux runtime

Evidence-driven reconstruction of *Need for Speed: SHIFT* with one practical milestone: a native offline Linux/Vulkan playable slice driven by original retail resources.

The repository already contains a connected retail-resource pipeline, Silverstone scene reconstruction, native Vulkan execution, a continuous runtime shell, persistent BMW physics state, exact selected-session scheduler timing, a proven BMW render/physics frame bridge, freshness-gated vehicle world-transform publication, and a progressively internalized retail `FUN_00766510` contact-response path.

It is **not yet a complete playable native build**. Current work is concentrated on the shortest remaining retail-semantic path needed to close the first Silverstone + BMW vertical slice.

## Milestone

```text
Silverstone
+
real retail BMW M3 E36
+
resource-driven bootstrap
+
input
+
continuous persistent physics
+
fresh vehicle world transform
+
camera
+
Vulkan rendering
=
native playable Linux vertical slice
```

The project is not trying to decompile every `SHIFT.exe` function before this milestone. Work that does not shorten an active blocker, produce evidence required by the next edge, or create immediately reusable infrastructure for that edge is deferred.

## Active development model

The first playable slice uses **three active parallel processes with explicit ownership**.

```text
PROCESS 1
retail proof / ABI / producer / timing
        |
        v
PROCESS 2
native physics / runtime execution
        |
        v
PROCESS 3
resources / scene / renderer / playable bootstrap
        |
        v
native playable Linux vertical slice
```

Canonical coordination files:

- [`PROCESS_INSTRUCTIONS.md`](PROCESS_INSTRUCTIONS.md)
- [`docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md`](docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md)
- [`docs/PLAYABLE_SLICE_THREE_PROCESS_PROMPTS_V6.md`](docs/PLAYABLE_SLICE_THREE_PROCESS_PROMPTS_V6.md)
- [`evidence/playable_slice_three_process_execution.json`](evidence/playable_slice_three_process_execution.json)

The v5 single-process coordination files remain historical records and do not select new work.

Before substantial work, answer:

> **Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

### Current process queues

**Process 1 — retail proof / provenance / timing**

```text
P1.1  close remaining FUN_00766510 dynamic-writer / optional-branch / residual-state ownership
P1.2  prove FUN_00765c40 collision-provider/load-term/residual ownership
P1.3  close input -> drivetrain/wheel/control producer chain
P1.4  prove retail camera-follow source/timing
```

**Process 2 — native physics / runtime**

```text
P2.1  consume Phase747 shared-reference-vector ownership without inventing dynamic source values
P2.2  consume the remaining P1.1 FUN_00766510 branch/state proofs in exact retail order
P2.3  remove complete contact_response when behavior is fully internal; target providers 7 -> 6
P2.4  consume P1.2 and narrow/remove residual FUN_00765c40
P2.5  replace remaining provider boundaries in dependency order
P2.6  consume the proven retail control chain continuously
```

**Process 3 — resources / scene / renderer / bootstrap**

```text
P3.1  merge resource-pipeline -> playable-scene provenance join (#1431)
P3.2  merge provenance-gated playable launcher/profile preparation (#1442, #1443)
P3.3  merge one-command playable resource-pipeline bootstrap (#1444)
P3.4  preserve exact Silverstone/BMW resource + participant authority
P3.5  consume fresh vehicle transform and later camera handoff
P3.6  final continuous Silverstone + BMW smoke path
```

Processes may advance in parallel on independent items. Cross-process handoffs must be explicit fail-closed contracts; one process does not invent another process's unresolved semantics.

## Current status

Current `main` frontier: **Phase 747**.

| Area | State | Notes |
| --- | --- | --- |
| Retail resource extraction / typed parsing | Ready for current slice | BFF Type 0/1/2 and X12d=2 supported; Type 3 still needs an external Oodle-compatible runtime |
| Silverstone scene reconstruction | Ready enough for slice integration | Scene placement, geometry, material/shader admission and native scene submission exist |
| Native XCB/Vulkan runtime | Ready | Window, device/swapchain, indexed draws, scene submission, shaders, textures and state transport are implemented |
| Continuous native session | Ready as infrastructure | Persistent runtime state, input transport, camera state, physics state and Vulkan submission coexist in one session |
| BMW BODY0 identity / bind frame | **Positive** | Retail BMW chassis BODY0 and BODY0-to-render-root bridge are proven |
| Fresh BMW world transform | **Positive** | Persistent BODY0 state can publish a freshness-gated BMW world transform |
| Retail outer scheduler/cadence | **Positive and consumed** | Native scheduler authority seam is active |
| Selected-session inner physics rate | **Positive and consumed** | Exact PC retail `PhysicsTweaker` rate is **180 Hz** |
| Retail inner BODY execution | **Positive** | Exact **1/180 s** persistent inner substeps are admitted; normal outer update resolves to six recovered substeps |
| `FUN_007682c0` BODY0 delta/effect path | **Largely native** | BODY0 destination, machine effect, x87 FSQRT, derived projection state and steering angle path are internalized |
| `FUN_00765c40` collision/query pass | **Partially native** | World position, query-cache lifetime, selected miss fallback and typed selected `CollisionQueryOutput` are available; collision provider/load terms/residual side effects remain external |
| `FUN_00766510` contact response | **Partially native, narrowed through Phase 747** | Same-pass collision/application-point handoff, primary caller accumulator delta, and shared reference-vector owner/transform are recovered; dynamic participant source materialization, optional branch integration and residual state/diagnostic writes still block removal |
| External top-level vehicle providers | **7 remain** | The count falls only when a complete callback can be removed without dropping source-visible behavior |
| Input -> drivetrain/wheel/control mapping | Incomplete | Live input exists, but full retail control producer/consumer mapping is not closed |
| Retail camera follow | Incomplete | Camera transport exists; authoritative follow source/timing is still open |
| Resource-pipeline -> playable bootstrap | **Implemented in open Process 3 stack, not yet on `main`** | Provenance join, launcher/profile wrappers and one-command orchestration are in #1431/#1442/#1443/#1444 |
| End-to-end playable Linux slice | **Not yet** | Core physics/control/camera and final integration blockers remain |

## What Phases 745–747 close

Phase 745 threads the same-pass selected `CollisionQueryOutput`, native `+0x38e0/+0x38e8` state and Phase 743 application point through `NativeVehicleProviderSession` into the residual `FUN_00766510` callback.

Phase 746 exposes the primary caller accumulator delta after `FUN_007baa70` using the recovered `FUN_00753650` cross-product path.

Phase 747 closes the owner and transform for the shared `local_d8/local_d0/local_c8` reference vector used by the early `+0x3b20` response branch and later contact-response work:

```text
HDVehicle+0x3fe8
  -> actual participant
  -> f32 +0x16b4/+0x16b8/+0x16bc
  -> independent f32 -> f64 widening
  -> FUN_007af0a0(BODY0+0xd4)
  -> local_d8/local_d0/local_c8
```

The source vector is **not** an immutable setup constant. `FUN_00713630` dynamically refreshes its X/Z participant lanes, with the source-visible cadence reached from `FUN_007144a0`. Phase 747 intentionally does not manufacture those dynamic values.

Phases 745–747 therefore narrow the residual callback substantially but do **not** remove `FUN_00765c40` or `contact_response`. The active top-level provider count remains seven.

## Current shortest native integration blocker

The first architectural provider reduction remains:

```text
complete FUN_00766510/contact_response internalization
        -> active external providers 7 -> 6
```

The immediate source/native boundary is now concrete rather than anonymous:

```text
FUN_00713630 dynamic participant X/Z writer state
        +
optional FUN_00766510 +0x3bc8/+0x3cxx branch
        +
remaining residual state/diagnostic writes
        -> exact-order native consumption
        -> remove top-level contact_response provider
```

Do not replace the unresolved dynamic participant state with a selected-session constant.

Process 1 PR **#1459** proves the optional `FUN_00766510` branch rooted at `HDVehicle+0x3bc8/+0x3cxx`, including setup-owned coefficients and the mutable `+0x3bd0` state. It is still open and therefore must not be treated as merged into `main`.

## Active work not yet on `main`

The following work is ahead of Phase 747 and should not be treated as merged until it lands:

- **Process 1 / PR #1459** — optional `FUN_00766510` `+0x3bc8/+0x3cxx` response-branch ownership; complete `contact_response` removal remains false after this proof alone.
- **Process 1** — close the remaining dynamic `FUN_00713630` participant-source state plus residual `FUN_00766510` state/diagnostic writes; continue the input/control and camera provenance queues.
- **Process 2** — consume the remaining proven `FUN_00766510` pieces in exact source order and remove `contact_response` only when no source-visible behavior is dropped.
- **Process 3 / PR #1431** — prove the exact resource-pipeline -> playable-scene provenance join.
- **Process 3 / PR #1442** — provenance-gated playable pipeline launcher.
- **Process 3 / PR #1443** — playable resource-pipeline profile preparation.
- **Process 3 / PR #1444** — one-command playable resource-pipeline bootstrap, stacked on #1443 -> #1442 -> #1431.

## Remaining external vehicle boundaries

The persistent `NativeVehicleProviderSession` still has seven top-level external boundaries:

```text
1. FUN_00765c40 residual collision/query pass
2. FUN_00758b50 wheel update
3. FUN_00766510 residual contact response
4. FUN_007675f0 remaining caller-input provider
5. FUN_007afdd0 scalar-provider factory
6. FUN_00765470 half-step refresh provider
7. FUN_007b8810 post-half-step provider
```

This number is a useful architectural metric. A provider is not removed merely because one field became native; it falls only when the full externally required behavior has been split, proven and consumed internally.

## What already works

### Retail resource pipeline

```text
BFF
  -> extraction / decompression / hashes
  -> typed format analysis
  -> neutral resource IR
  -> scene / render / physics contracts
```

Main entry point:

```bash
python shift_importer.py --help
```

BFF-specific tooling is documented in [`BFF_TOOLS.md`](BFF_TOOLS.md).

### Silverstone and BMW scene path

```text
SGB
  -> NODE / SUMM / PART / FLAT / OBJECT
  -> scene placement
  -> MeshInst resolution
  -> IMB / IMX geometry
  -> material + shader binding
  -> runtime-evidence admission
  -> NativeSceneBundle
  -> NativeSceneVulkanSet
  -> Vulkan execution
```

The selected BMW render path uses the exact retail model:

```text
vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

Static VHF object-frame transport remains separate from dynamic vehicle pose.

### BMW frame and persistent transform

Closed pieces include:

- retail BMW chassis BODY index `0` identity;
- BODY0 resource/local -> SDF bind facts;
- selected-session BODY0 -> outer Vehicle numeric relation;
- outer Vehicle -> BMW VHF root relation;
- `SHIFT.BMWBody0BindFrameProof/1`;
- persistent BODY freshness tracking;
- `SHIFT.BMWPersistentWorldTransformRuntimeWiring/1`;
- Vulkan-side freshness-gated vehicle transform consumption.

The renderer transport is no longer the main blocker for authentic vehicle motion.

### Vehicle physics

The native source-backed path already contains substantial pre-PhysX / SDF numerical runtime infrastructure:

```text
CDF + EDF + GDF + SDF
  -> VehiclePhysicsAssetGraph
  -> participant / selector boundaries
  -> BODY + JOINT / HINGE / BAR state
  -> matrix / RHS assembly
  -> reset / sparse solve
  -> post-solve BODY projection
  -> wheel/contact response primitives
  -> persistent native BODY state
```

Implemented pieces include:

- generated BODY constraint/matrix assembly;
- JOINT/HINGE/BAR projection and coupling kernels;
- builtin diagonal reset and sparse solve;
- post-solve BODY projection;
- BODY point transforms and accumulator helpers;
- wheel/contact response arithmetic;
- persistent BMW BODY state and freshness;
- exact selected-session 180 Hz inner timing;
- exact 1/180 s persistent inner execution;
- source-backed BODY0 delta destination and application;
- native `FUN_007682c0` machine effect with x87 behavior preserved;
- native derived projection state;
- native `FUN_007594e0` steering/machine-angle path;
- native pieces of `FUN_00765c40` query-state ownership;
- typed selected `CollisionQueryOutput` and query-scalar handoff;
- native primary `FUN_00766510` response application;
- same-pass `FUN_00766510` collision/application-point session handoff;
- primary `FUN_00766510` caller accumulator delta through recovered `FUN_00753650`;
- shared `FUN_00766510` reference-vector owner plus exact f32 -> f64 -> BODY-frame transform boundary.

This is still **not a complete retail vehicle frame**. Remaining producer/refresh ownership, residual collision/contact callbacks, control production and camera timing must be closed before the project can claim a playable retail-consistent loop.

### Input and camera

Already implemented:

- live X11 keyboard control intent;
- deterministic scripted input for regressions;
- CameraManager state transport;
- guarded camera double-buffer updates;
- camera state carried in the continuous native session.

Still missing:

- exact retail input -> drivetrain/wheel/control producer mapping;
- continuous execution of the fully proven control chain;
- authoritative camera-follow source and timing tied to the current admitted vehicle transform.

### Continuous runtime

The Linux runtime is an integrated persistent execution shell rather than a one-frame renderer test:

```text
resource-backed scene
  + native runtime state
  + input
  + camera state
  + persistent BMW physics state
  + exact selected-session inner timing
  -> continuous native session
  -> Vulkan frame submission
```

Host wall-clock pacing remains an execution policy and is not used as a substitute for recovered retail scheduler evidence.

## Native vertical-slice launcher

The integration runner consumes a profile instead of a long manually assembled command line:

```bash
python3 tools/run_native_vertical_slice.py \
  out/vertical_slice/profile.json \
  --dry-run \
  --json-out out/vertical_slice/launch_plan.json
```

Launch after all required profile gates are ready:

```bash
python3 tools/run_native_vertical_slice.py \
  out/vertical_slice/profile.json
```

The Process 3 stack extends this with a provenance-gated playable-pipeline profile/launcher/bootstrap path, but #1431/#1442/#1443/#1444 are not yet merged into `main`.

A valid launch profile proves structural/runtime admission only; it does not by itself prove gameplay-semantic completeness.

## Evidence policy

The repository deliberately stays fail-closed.

- PC retail is the primary semantic authority.
- Xbox 360 recompilation may be used as independent navigation/corroboration, not as a replacement for PC proof.
- Static executable evidence, runtime observations and resource identity remain separate until explicitly joined.
- Callgraph proximity is not ownership.
- Equal numeric values are not provenance.
- Visual similarity is not resource identity.
- Static VHF transforms are not dynamic vehicle pose.
- Missing proof remains a blocker instead of being guessed.
- Host pacing cannot stand in for retail scheduler evidence.
- Fixtures and test scripts cannot satisfy retail-semantic gates.
- A native implementation is not automatically treated as recovered retail behavior.

Cross-process contracts are explicit handoffs: Process 1 proves semantics, Process 2 consumes them in native runtime, and Process 3 consumes admitted runtime/resource state for the visible playable slice.

## Ghidra and runtime evidence

Static analysis is exported into machine-readable evidence instead of remaining only inside an interactive Ghidra project. Targeted instruction/p-code exports are used when a blocker needs exact register/value/store provenance.

Typical export:

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_shift_export.sh \
  /path/to/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/shift_ghidra_database
```

`native_capture/`, `src/graphics/d3d9/` and bounded physics/runtime probes cover runtime evidence that cannot be recovered uniquely from static code. Runtime capture is requested only when the current blocker cannot be closed from static/resource evidence.

## Build and test

### Python

```bash
./install_requirements.sh
source .venv/bin/activate
python -m pytest -q
```

Live-memory tooling:

```bash
make -C tools/shift_live_dump test
```

### Native Linux runtime

Dependencies include Vulkan, XCB and `glslangValidator`.

```bash
cmake -S native_runtime -B native_runtime/build -DCMAKE_BUILD_TYPE=Release
cmake --build native_runtime/build --parallel
ctest --test-dir native_runtime/build --output-on-failure
```

### Native Vulkan utilities

```bash
cmake -S native_vulkan -B native_vulkan/build -DCMAKE_BUILD_TYPE=Release
cmake --build native_vulkan/build --parallel
```

CI exercises software Vulkan/lavapipe paths, shader compilation/reflection, scene/material submission, runtime contracts and focused native-physics regressions. Phase 747 adds a focused Python + native CTest + evidence-validation workflow for the shared `FUN_00766510` reference-vector boundary.

## Repository layout

```text
native_runtime/        native XCB/Vulkan runtime and physics execution
native_vulkan/         native Vulkan preparation/utilities
native_capture/        retail D3D9 capture support
src/resources/         resource formats and neutral resource contracts
src/graphics/          render/material/shader reconstruction
src/physics/           vehicle physics analysis and native handoff builders
tools/ghidra/          static proof and targeted Ghidra analyzers
tools/shift_live_dump/ bounded live-memory analysis tooling
evidence/              source-backed evidence/manifests/contracts
docs/                  proof-boundary and phase documentation
tests/                 Python/source-contract regressions
```

## Scope and non-goals

The current target is an **offline native runtime** for original retail content.

The first playable slice intentionally does not require:

- EA services;
- DRM;
- login/profile/cloud services;
- matchmaking or online networking;
- Bink/video playback;
- Android support.

Android remains deferred until the desktop/native runtime boundary is stable.

## Definition of the first playable slice

The milestone is reached only when one continuous native session satisfies all of the following:

```text
[x] authentic Silverstone resource pipeline exists
[x] exact retail BMW render/physics identity is established
[x] persistent BMW BODY state exists
[x] retail outer cadence is admitted
[x] selected-session 180 Hz inner rate is admitted
[x] exact 1/180 s persistent inner execution exists
[x] BODY0 can publish a fresh admitted vehicle world transform
[x] selected FUN_00765c40 collision output is typed for the BMW path
[x] same-pass FUN_00766510 handoff and primary caller accumulator path are native/proven
[x] shared FUN_00766510 reference-vector owner/transform is proven
[ ] dynamic participant source and remaining FUN_00766510 residual branches/state are fully internalized
[ ] residual vehicle provider callbacks needed by the core loop are eliminated or reduced to proven resource/runtime inputs
[ ] user input reaches the complete source-backed drivetrain/wheel/control chain
[ ] camera follows the proven current vehicle source/timing
[ ] Silverstone + BMW runs continuously without test-only core motion
[ ] no unsupported semantic guess is required for the core loop
```

Until every required item is true, the repository should be described as an **advanced decompilation/reconstruction with a functioning native Linux runtime and a partially internalized retail vehicle-physics loop**, not as a finished native port.
