# Need for Speed: SHIFT — decompilation and native Linux runtime

Evidence-driven reconstruction of *Need for Speed: SHIFT* with one practical target: a native offline Linux/Vulkan playable slice using the original retail resources.

The repository is no longer only an extractor or a collection of isolated reverse-engineering notes. It now contains a connected resource pipeline, scene reconstruction, renderer contracts, native Vulkan execution, camera/input state, a substantial source-backed vehicle-physics path, persistent BODY state infrastructure, and a continuous native runtime loop.

The project is **not yet a complete playable native build**. The remaining work is concentrated in a small number of evidence-gated joins around the real vehicle update path rather than in basic parsing or window/render bootstrap.

## Current target

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

Current development is coordinated as three processes that must converge on that slice:

```text
PROCESS 1
static proof / ABI / producer / scheduling
        │
        ▼
PROCESS 2
native physics/runtime execution
        │
        ├─────────────────────────┐
        │                         │
        ▼                         ▼
persistent vehicle        PROCESS 3
                          resources/scene/render
        │                         │
        └────────────┬────────────┘
                     ▼
            playable Linux slice
```

## Current checkpoint

The native runtime has progressed through the continuous-session work of Phases 709/710:

- explicit `--continuous` execution until window quit;
- fixed `1/60` native simulation boundary;
- host wall-clock pacing with `std::chrono::steady_clock` for continuous mode;
- persistent native runtime state across ticks;
- live input, camera-state transport, physics state and Vulkan submission inside the same session.

This pacing is a **native execution policy**, not a claim that the retail game used the same outer-update schedule. Retail cadence ownership remains evidence-gated.

The current Process 1 frontier is the BMW BODY0 bind/initialization chain. We already have source-backed evidence for:

- BMW chassis identity as BODY index `0`;
- persistent BODY pose storage;
- BODY0 origin at `+0x00/+0x08/+0x10` as `f64`;
- BODY0 basis at `+0xd4..+0xf4` as `f32`;
- the persistent BODY0 → vehicle world-matrix transport path;
- live Vulkan consumption of that persistent vehicle transform.

The missing semantic proof is still `SHIFT.BMWBody0BindFrameProof/1`: the exact source-backed construction/bind producer for the persistent BODY0 origin/basis values.

## What already works

### Resource pipeline

```text
BFF
  -> extraction / decompression / hashes
  -> typed format analysis
  -> neutral resource IR
  -> scene / render / physics contracts
```

The active corpus supports SHIFT BFF Type 0/1/2 extraction and X12d=2 encryption. Type 3 remains dependent on an externally supplied Oodle-compatible runtime.

Main entry point:

```bash
python shift_importer.py --help
```

BFF-specific tooling is documented in [`BFF_TOOLS.md`](BFF_TOOLS.md).

### Silverstone / scene path

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

The Silverstone Era3 dependency surface is structurally well reconstructed. Scene placement, neutral geometry and native scene submission are implemented. Remaining render-side ambiguity is kept fail-closed instead of choosing tied shaders, renderer-owned resources or transform history heuristically.

### Native Vulkan renderer

The native renderer already provides:

- XCB window creation;
- Vulkan instance/device/surface/swapchain setup;
- indexed multi-draw submission;
- neutral scene-set execution;
- semantic-aware affine transforms;
- SPIR-V shader loading;
- constant-buffer transport;
- 2D textures and supported cube resources;
- per-draw cull/depth/blend state for the proven material subset;
- Vulkan validation-oriented regression paths;
- live persistent-vehicle vertex upload infrastructure.

The renderer transport itself is no longer the main blocker for visible vehicle motion.

### Vehicle physics

The source-backed native physics path includes substantial portions of the pre-PhysX / SDF numerical runtime:

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

Implemented native work includes, among other pieces:

- BODY accumulator helpers;
- JOINT/HINGE/BAR projection and matrix-coupling kernels;
- generated BODY constraint/matrix assembly;
- builtin diagonal reset and sparse solve execution;
- post-solve BODY projection;
- BODY point transforms;
- wheel/contact response arithmetic;
- auxiliary contact-response chaining;
- source-backed wheel-force aggregation;
- persistent BODY pose storage and freshness checks;
- persistent BMW vehicle world-transform transport.

These components do **not** yet constitute a complete retail vehicle frame. Several caller-side producers, scheduling joins and control inputs remain independent gates.

### Input and camera

The native runtime has:

- live X11 keyboard control intent;
- deterministic input scripts for regression tests;
- recovered CameraManager state transport;
- guarded camera double-buffer updates;
- camera state carried inside the native fixed-step session.

Still unresolved are the exact retail control-producer mapping into drivetrain/wheel state and the final retail-consistent camera-follow source/timing.

### Continuous native runtime

The current Linux runtime is an integrated execution shell rather than a one-frame renderer test:

```text
resource-backed scene
  + native runtime state
  + input
  + camera
  + physics packets/state
  + persistent vehicle state
  -> continuous 1/60 native session
  -> Vulkan frame submission
```

`--continuous` is paced against host wall time. Bounded and scripted runs remain deterministic and unpaced for regression purposes.

## Main blocker graph

The shortest path to the first playable Linux slice is now:

```text
PROCESS 1
BODY0 construction/bind writer provenance
        │
        ▼
positive SHIFT.BMWBody0BindFrameProof/1
        │
        ▼
retail-admissible persistent BODY0 pose
        │
        ├───────────────┐
        ▼               ▼
physics producers   vehicle world transform
+ retail cadence         │
+ control mapping        ▼
        │          live Vulkan vehicle update
        └───────┬───────┘
                ▼
         camera follow source
                │
                ▼
        playable Linux slice
```

The highest-priority remaining blockers are:

1. **Positive BODY0 bind-frame proof.** Identify the exact construction/bind writes and value provenance for persistent BMW BODY0 origin/basis.
2. **Missing external vehicle-physics producers.** Promote source-backed producer paths from the current provider frontier into native execution instead of fabricating inputs.
3. **Retail outer-update cadence ownership.** Connect the recovered explicit vehicle update to its exact scheduler/caller rather than equating it with the current host `1/60` loop.
4. **Input → drivetrain/wheel producer mapping.** The neutral control-intent boundary exists, but retail force/control semantics still need proof.
5. **Camera follow source.** Once a current retail vehicle transform is admissible, connect the recovered camera state to that source with source-consistent timing.
6. **Remaining exact scene/runtime resource joins.** Resolve tied shader/resource cases and renderer-owned resources where runtime evidence is still required.

Work that does not shorten this graph, or create reusable infrastructure required by its next edge, should be deferred.

## Evidence policy

The repository is deliberately fail-closed.

- Static executable evidence, runtime observations and reconstructed contracts remain separate.
- Ambiguous values stay ambiguous.
- Missing proof is represented as a blocker rather than guessed.
- Runtime-owned renderer resources are not silently synthesized.
- Native execution requires explicit provenance/admission gates in addition to structurally valid data.
- A native implementation is not automatically treated as recovered retail behavior.

Common evidence states include:

```text
proven
verified
inferred
ambiguous
unknown
unsupported
blocked
```

The goal is not merely to make something visually similar to SHIFT; it is to reconstruct the original behavior as far as the available evidence permits while keeping unsupported assumptions visible.

## Ghidra evidence database

Static analysis is exported into machine-readable evidence rather than being left only in an interactive Ghidra project. The database includes functions, callgraph edges, strings/xrefs, globals, static data, switch candidates, factory candidates, constructors and vtable candidates.

Typical export:

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_shift_export.sh \
  /path/to/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/shift_ghidra_database
```

Targeted instruction/p-code exports are used when a blocker requires exact register/value/store provenance instead of broad decompiler output.

The active BODY0 construction-pose pass is documented in:

[`docs/PROCESS_1_BMW_BODY0_CONSTRUCTION_POSE_STORES.md`](docs/PROCESS_1_BMW_BODY0_CONSTRUCTION_POSE_STORES.md)

## Runtime evidence

Static analysis cannot uniquely recover every runtime identity. The repository therefore contains bounded capture and audit paths for observations that require the retail executable.

### D3D9 capture

`native_capture/` and `src/graphics/d3d9/` provide capture/audit/attribution tooling for:

- tied FXO permutations;
- draw-local texture/resource identity;
- Silverstone IMB draw attribution;
- runtime transforms;
- same-instance shader/resource proof;
- renderer-owned resources.

### Physics/runtime capture

`tools/` contains bounded runtime probes, evidence packaging and verification helpers for vehicle/provider behavior that cannot be recovered uniquely from static code alone.

Runtime capture should be requested only when the exact blocker cannot be closed from the existing static database.

## Native vertical-slice launcher

The integration runner consumes a single profile instead of requiring a long manually assembled command line:

```bash
python3 tools/run_native_vertical_slice.py \
  out/vertical_slice/profile.json \
  --dry-run \
  --json-out out/vertical_slice/launch_plan.json
```

Launch after all profile gates are ready:

```bash
python3 tools/run_native_vertical_slice.py \
  out/vertical_slice/profile.json
```

The launch contract verifies the already-implemented scene, camera, participant/physics and native packet boundaries. A valid launch profile does not by itself prove full gameplay semantics.

## Build and test

### Python

Python 3.9+ is required by the repository bootstrap script.

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

CI exercises software Vulkan/lavapipe paths, shader compilation/reflection, validation checks, scene/material submission, runtime contracts and focused native-physics regressions.

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
docs/                  phase and proof-boundary documentation
tests/                 Python/source-contract regressions
```

## Scope and non-goals

The current target is an **offline native runtime** for original retail game content.

The first playable slice intentionally does not require:

- EA services;
- DRM;
- login/profile/cloud services;
- matchmaking or online networking;
- Bink/video playback;
- Android support.

Those are outside the current blocker graph. Android remains deferred until the desktop/native runtime boundary is stable.

## Definition of the next milestone

The next milestone is reached when the repository can start from authentic retail resources and produce one continuous Linux session in which:

- Silverstone is loaded through the resource pipeline;
- a real BMW vehicle is instantiated;
- input affects the source-backed vehicle update path;
- physics state persists across ticks;
- BODY0 produces the current vehicle world transform;
- the camera follows that current transform;
- Vulkan renders the changing scene/vehicle continuously;
- no test-only transform script or unsupported semantic guess is required for the core loop.

Until those conditions are true, the project should be described as an advanced reconstruction/runtime integration effort rather than a finished native port.
