# Need for Speed: SHIFT — decompilation and native Linux runtime

Evidence-driven reconstruction of *Need for Speed: SHIFT* with one practical target: a native offline Linux/Vulkan playable slice using the original retail resources.

The repository is no longer only an extractor or a collection of isolated reverse-engineering notes. It contains a connected retail-resource pipeline, Silverstone scene reconstruction, renderer contracts, native Vulkan execution, camera/input state transport, a substantial source-backed vehicle-physics path, persistent BODY state infrastructure, and a continuous native runtime loop.

The project is **not yet a complete playable native build**. The remaining work is concentrated in a short evidence-gated chain around the real BMW vehicle transform, retail update cadence, control producers, and camera-follow timing rather than in basic parsing, window creation, or Vulkan bootstrap.

## Current target

```text
Silverstone
+
real retail BMW
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

Development now uses **one active process** and one sequential critical path:

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

Canonical coordination rules are in:

- [`PROCESS_INSTRUCTIONS.md`](PROCESS_INSTRUCTIONS.md)
- [`docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md`](docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md)
- [`docs/PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md`](docs/PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md)
- [`evidence/playable_slice_single_process_execution.json`](evidence/playable_slice_single_process_execution.json)

The former Process 1 / Process 2 / Process 3 ownership model and blocker-swarm coordination are retired. Historical contract/file names containing `Process1`, `Process2`, or `Process3` remain stable evidence/ABI identifiers only; they no longer imply separate workers or waiting handoffs.

## Current checkpoint

The native runtime has already progressed through the continuous-session work of Phases 709/710 and later persistent-vehicle wiring:

- explicit `--continuous` execution until window quit;
- fixed `1/60` native simulation boundary;
- host wall-clock pacing with `std::chrono::steady_clock` for continuous mode;
- persistent native runtime state across ticks;
- live input, camera-state transport, physics state and Vulkan submission inside the same session;
- persistent BODY0 pose storage and generation/freshness checks;
- production-side persistent vehicle transform transport into the Vulkan vehicle upload path.

The host `1/60` loop is a **native execution policy**, not proof of the retail game's outer-update schedule. Retail cadence ownership remains independently evidence-gated.

### BMW BODY0 / VHF proof state

The major semantic frame uncertainty has been reduced substantially.

Already positive on `main`:

- retail BMW chassis BODY index `0` identity;
- BODY0 resource/local → SDF bind facts;
- selected-session BODY0 → outer Vehicle numeric relation;
- `SHIFT.BMWBody0VHFBindFrameFrontier/1` composition formula;
- `SHIFT.BMWVehicleRenderModelResourceJoin/1`;
- exact canonical BMW render model `vehicles/bmw_m3_e36/bmw_m3_e36.vhf`;
- `SHIFT.BMWVHFHierarchyRootFrame/1`;
- `SHIFT.OuterVehicleRenderSnapshotAffineBridge/1`;
- `SHIFT.OuterVehicleRenderRootDeltaProvenance/1`;
- `SHIFT.VehicleRenderModelRootAffineDomainJoin/1`;
- `SHIFT.OuterVehicleBMWVHFRootRelation/1`;
- `SHIFT.BMWVHFRootFrameSceneConsumer/1`;
- persistent BODY/runtime transport and freshness infrastructure;
- live Vulkan vehicle-transform sink;
- strict relation/final bind admission seams.

`SHIFT.OuterVehicleBMWVHFRootRelation/1` proves that the outer Vehicle root → canonical BMW VHF `HIERARCHY Root` relation is **setup-fixed affine** for an initialized vehicle instance. The identity-vs-affine semantic question is therefore closed.

Under the established D3D row-vector convention:

```text
M_vhf_root_to_outer = M_vhf_root_to_model * T(delta_local)
M_outer_to_vhf_root = inverse(M_vhf_root_to_model * T(delta_local))
```

with:

```text
delta_local = outerVehicle[+0x19c,+0x1a0,+0x1a4]
producer    = FUN_00795d60
lifetime    = Vehicle::InitVehicle setup state
```

The remaining blocker is **numeric materialization** of those three selected-BMW setup scalars with exact provenance. Until that is done, the finite outer→VHF matrix and final BODY0 bind matrix remain unavailable.

Current fail-closed gates:

```text
outer_vehicle_root_to_VHF_relation_numeric_matrix_ready = false
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready    = false
BODY0_bind_frame_proof_ready                            = false
vehicle_world_transform_ready                           = false
retail_cadence_admitted                                 = false
retail_control_chain_complete                           = false
retail_camera_follow_ready                              = false
```

The proof behind the positive semantic relation is documented in [`docs/PROCESS_1_OUTER_VEHICLE_BMW_VHF_ROOT_RELATION.md`](docs/PROCESS_1_OUTER_VEHICLE_BMW_VHF_ROOT_RELATION.md). The historical `Process 1` name in that filename is retained for traceability; active development is single-process.

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

The Silverstone Era3 dependency surface is structurally well reconstructed. Scene placement, neutral geometry and native scene submission are implemented. Remaining render-side ambiguity stays fail-closed instead of choosing tied shaders, renderer-owned resources, or transform history heuristically.

The BMW production scene path also consumes the exact canonical VHF identity and hierarchy-root frame. Static VHF object-frame transport is kept distinct from dynamic vehicle pose.

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

The renderer transport itself is no longer the main blocker for visible authentic vehicle motion. It is waiting on the final evidence-admitted dynamic BMW world transform rather than another render transform mechanism.

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

These components do **not** yet constitute a complete retail vehicle frame. The remaining semantic bind, scheduler, producer, and control gates stay separate from the mechanical runtime infrastructure.

### Input and camera

The native runtime has:

- live X11 keyboard control intent;
- deterministic input scripts for regression tests;
- recovered CameraManager state transport;
- guarded camera double-buffer updates;
- camera state carried inside the native fixed-step session.

Still unresolved are the exact retail control-producer mapping into drivetrain/wheel state and the retail-consistent camera-follow source/timing. Camera follow must consume an admitted current vehicle transform rather than a test-only or stale transform.

### Continuous native runtime

The current Linux runtime is an integrated execution shell rather than a one-frame renderer test:

```text
resource-backed scene
  + native runtime state
  + input
  + camera
  + physics packets/state
  + persistent vehicle state
  -> continuous native session
  -> Vulkan frame submission
```

`--continuous` is paced against host wall time. Bounded and scripted runs remain deterministic and unpaced for regression purposes.

## Main blocker graph

The shortest path to the first playable Linux slice is now:

```text
SHIFT.OuterVehicleBMWVHFRootRelation/1        [POSITIVE semantic relation]
        |
        v
selected BMW Vehicle::InitVehicle delta_local
+0x19c / +0x1a0 / +0x1a4                    [CURRENT BLOCKER]
        |
        v
finite provenance-backed M_outer_to_vhf_root
        |
        v
compose already-positive BODY0 -> outer relation
        |
        v
SHIFT.BMWBody0BindFrameProof/1
        |
        v
persistent fresh BMW world transform
        |
        v
retail scheduler/cadence + missing physics/control producers
        |
        v
input -> drivetrain/wheels/control
        |
        v
retail camera-follow source/timing
        |
        v
Silverstone + BMW + continuous Vulkan
        |
        v
playable Linux slice
```

The single sequential queue is:

1. **Materialize the exact selected-BMW `FUN_00795d60` setup delta.** Recover the three `Vehicle::InitVehicle` scalars at outer Vehicle `+0x19c/+0x1a0/+0x1a4` from exact producer/value provenance.
2. **Evaluate the finite outer→VHF matrix.** Consume the already-positive setup-fixed affine relation; do not reopen identity-vs-affine semantics.
3. **Publish positive `SHIFT.BMWBody0BindFrameProof/1`.** Compose the positive BODY0→outer relation with the finite outer→VHF matrix.
4. **Admit and publish a fresh persistent BMW world transform.** Consume the proof through the already-existing native packet/freshness/Vulkan seams.
5. **Prove retail outer-update scheduler/cadence ownership.** Host `1/60` is not retail evidence.
6. **Close the deepest missing vehicle-physics/control producers.** Internalize only source-backed producer/owner handoffs.
7. **Close input → drivetrain/wheel/control mapping.** Execute the proven control chain continuously.
8. **Prove and consume retail camera-follow source/timing.** Follow the current admitted vehicle transform.
9. **Run Silverstone + exact BMW resources + persistent physics + camera + Vulkan continuously** without a test-only core-motion script or unsupported semantic guess.

Work that does not shorten this chain, or build reusable infrastructure immediately required by its next blocked edge, should be deferred.

## Evidence policy

The repository is deliberately fail-closed.

- Static executable evidence, runtime observations, resource identity, and reconstructed contracts remain separate until explicitly joined.
- Callgraph proximity is not ownership.
- Equal numeric values are not provenance.
- Visual similarity is not resource identity.
- Identity-valued matrices do not prove identity semantics.
- Static VHF object transforms are not dynamic vehicle pose.
- Missing proof is represented as a blocker rather than guessed.
- Runtime-owned renderer resources are not silently synthesized.
- Native execution requires explicit provenance/admission gates in addition to structurally valid data.
- Host `1/60` pacing is not retail scheduler evidence.
- Fixtures and test scripts cannot satisfy retail-semantic gates.
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

The current proof chain is intentionally narrow:

```text
Vehicle::InitVehicle / FUN_00798df0
  -> exact callsite 0x007990ed
  -> FUN_00795d60
  -> outerVehicle +0x19c/+0x1a0/+0x1a4
  -> finite outer/VHF matrix
  -> BMW BODY0 bind proof
```

No new original-game execution or runtime capture is requested while these setup values remain statically recoverable from the existing executable/resource evidence.

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

Runtime capture should be requested only when the exact current blocker cannot be closed from the existing static/resource database.

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
- the exact retail BMW render model is instantiated;
- input affects the source-backed vehicle update path;
- physics state persists across ticks;
- BODY0 produces a fresh admitted vehicle world transform;
- the camera follows that current transform with source-consistent timing;
- Vulkan renders the changing scene/vehicle continuously;
- no test-only transform script or unsupported semantic guess is required for the core loop.

Until those conditions are true, the project should be described as an advanced reconstruction/runtime integration effort rather than a finished native port.
