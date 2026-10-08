# Need for Speed: SHIFT — decompilation and native Linux runtime

Evidence-driven reconstruction of *Need for Speed: SHIFT* with one practical milestone: a native offline Linux/Vulkan playable slice driven by original retail resources.

The repository already contains a connected retail-resource pipeline, Silverstone scene reconstruction, native Vulkan execution, a continuous runtime shell, persistent BMW physics state, exact selected-session scheduler timing, a proven BMW render/physics frame bridge, and freshness-gated vehicle world-transform publication.

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

The project is not trying to decompile every `SHIFT.exe` function before this milestone. Work that does not shorten the active blocker, produce evidence required by the next edge, or create immediately reusable infrastructure for that edge is deferred.

## Active development model

The first playable slice now uses **one active development process**.

```text
static proof / ABI / provenance / scheduling
        -> native physics/runtime
        -> persistent vehicle + fresh world transform
        -> resources / scene / camera / Vulkan
        -> playable Linux slice
```

Canonical coordination files:

- [`PROCESS_INSTRUCTIONS.md`](PROCESS_INSTRUCTIONS.md)
- [`docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md`](docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md)
- [`docs/PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md`](docs/PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md)
- [`evidence/playable_slice_single_process_execution.json`](evidence/playable_slice_single_process_execution.json)

The old Process 1 / Process 2 / Process 3 lanes are historical compatibility/evidence names only; they no longer define active ownership.

Before substantial work, answer:

> **Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

## Current status

Current `main` frontier: **Phase 743**.

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
| `FUN_00765c40` collision/query pass | **Partially native** | World position, query-cache lifetime and selected miss fallback are native-owned; collision lookup/load terms/residual side effects remain external |
| `FUN_00766510` contact response | **Partially native** | Primary response application is native; Phase 743 proves the selected BMW application-point owner |
| External top-level vehicle providers | **7 remain** | The count must fall only when complete callbacks can be removed without dropping source-visible behavior |
| Input -> drivetrain/wheel/control mapping | Incomplete | Live input exists, but full retail control producer/consumer mapping is not closed |
| Retail camera follow | Incomplete | Camera transport exists; authoritative follow source/timing is still open |
| End-to-end playable Linux slice | **Not yet** | Core physics/control and final integration blockers remain |

## What Phase 743 closes

The selected BMW application-point source for the primary `FUN_00766510` response path is now proven.

```text
HDVehicle+0x38f0/+0x38f8/+0x3900
    = Phase 727 BODY0-basis transform result
    = Fun00765c40WorldPositionTransformResult.body_rotated_local
```

The same stored vector is later consumed by `FUN_00766510` as the point argument to the already-native primary response application.

This is deliberately distinct from the origin-added collision `world_position` used by the `FUN_00765c40` query.

Phase 743 does **not** remove the `contact_response` provider. The active top-level provider count remains seven.

See:

- [`docs/PHASE743_SCOPE.md`](docs/PHASE743_SCOPE.md)
- [`evidence/phase743_next_blocker.md`](evidence/phase743_next_blocker.md)

## Current shortest blocker

The next bounded integration edge is the handoff from the residual `FUN_00765c40` collision result into the remaining `FUN_00766510` / `contact_response` path.

Required chain:

```text
same-pass FUN_00765c40 collision/query result
        +
native HDVehicle+0x38e0 hit/miss state
        +
selected HDVehicle+0x38e8 fallback / clamp bound
        +
Phase 743 HDVehicle+0x38f0 application point
        v
typed FUN_00766510 response input
        v
native primary response application
        v
remaining contact-response state / auxiliary branches / writes
```

After that handoff, remaining response configuration owners include:

```text
HDVehicle+0x3908
HDVehicle+0x3910
HDVehicle+0x3918
HDVehicle+0x3950
```

The `contact_response` callback can only be removed after the earlier/optional branches, auxiliary calls and source-visible state/diagnostic writes are also preserved.

## Active work not yet on `main`

The following work is ahead of Phase 743 and should not be treated as merged until it lands:

- **Phase 744 / PR #1441** — expose typed selected-BMW `CollisionQueryOutput` from the residual `FUN_00765c40` boundary and derive the `FUN_00766510` query scalar handoff.
- **Phase 745 / PR #1445** — thread same-pass collision output, `+0x38e0/+0x38e8` state and the Phase 743 application point into the residual contact-response callback.
- **Phase 746 / PR #1447** — expose the primary `FUN_00766510` caller accumulator delta after `FUN_007baa70` using the recovered `FUN_00753650` cross-product path.
- Process 3 integration PRs are also building a provenance-gated resource-pipeline -> playable-scene -> profile -> launcher path for a one-command vertical-slice bootstrap.

These changes are important because they convert the old broad boundary

```text
FUN_00765c40 -> opaque external data -> FUN_00766510
```

into a progressively typed/native path:

```text
native query inputs
  -> typed collision output
  -> native clamp/config
  -> native response transform
  -> native application point
  -> native accumulator pieces
```

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
- native primary `FUN_00766510` response application.

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

Cross-process historical contracts remain useful evidence artifacts, but active development now consumes positive contracts immediately in the single-process blocker chain.

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

CI exercises software Vulkan/lavapipe paths, shader compilation/reflection, scene/material submission, runtime contracts and focused native-physics regressions.

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
[ ] residual vehicle provider callbacks needed by the core loop are eliminated or reduced to proven resource/runtime inputs
[ ] user input reaches the complete source-backed drivetrain/wheel/control chain
[ ] camera follows the proven current vehicle source/timing
[ ] Silverstone + BMW runs continuously without test-only core motion
[ ] no unsupported semantic guess is required for the core loop
```

Until every required item is true, the repository should be described as an **advanced decompilation/reconstruction with a functioning native Linux runtime and a partially internalized retail vehicle-physics loop**, not as a finished native port.
