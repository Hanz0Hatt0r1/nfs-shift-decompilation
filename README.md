# Need for Speed: SHIFT — decompilation and native Linux runtime

Evidence-driven reconstruction of *Need for Speed: SHIFT* with one practical milestone: a native offline Linux/Vulkan playable slice driven by original retail resources.

The repository already contains a connected resource pipeline, Silverstone scene reconstruction, native Vulkan execution, continuous runtime state, source-backed vehicle-physics infrastructure, persistent BMW BODY state, a proven BMW render/physics frame bridge, and a freshness-gated vehicle world-transform path.

It is **not yet a complete playable native build**. Current development is deliberately organized around the shortest blocker graph to the first playable Linux vertical slice.

## Milestone

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

The project is not trying to decompile every `SHIFT.exe` function before this milestone. Work that does not shorten the active blocker graph, produce evidence required by the next edge, or create immediately reusable infrastructure for that edge is deferred.

## Three-process execution model

All development is coordinated as one dependency chain:

```text
PROCESS 1
static proof / ABI / producer / scheduling
        |
        v
PROCESS 2
native physics/runtime execution
        |
        +-------------------------+
        |                         |
        v                         v
persistent vehicle          PROCESS 3
                            resources / scene / render
        |                         |
        +------------+------------+
                     v
            playable Linux slice
```

Canonical three-process coordination documents:

- [`docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V3.md`](docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V3.md)
- [`docs/PLAYABLE_SLICE_PARALLEL_PROCESS_PROMPTS.md`](docs/PLAYABLE_SLICE_PARALLEL_PROCESS_PROMPTS.md)

Before every substantial task, answer:

> **Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

Every blocker-sized task should identify:

```text
BLOCKER   concrete blocked edge being shortened
INPUT     exact evidence/contract already available
OUTPUT    exact proof/contract/runtime capability produced
CONSUMER  exact downstream process/path that consumes it
```

If the consumer cannot be named, the task is normally out of scope.

### Process ownership

**PROCESS 1 — static proof / ABI / producer / scheduling**

Owns retail semantic proof, ABI/value provenance, owner/producer identity, scheduler/cadence proof, control-producer mapping and camera source/timing proof. It emits narrow source-backed contracts for downstream consumers.

**PROCESS 2 — native physics/runtime execution**

Consumes positive Process 1 contracts, implements the corresponding native runtime behavior, maintains persistent physics state and freshness, and publishes the current vehicle world transform through fail-closed admission gates.

**PROCESS 3 — resources / scene / render**

Owns exact retail resource admission, Silverstone/BMW bootstrap composition, Vulkan execution, consumption of fresh Process 2 transforms, and visible slice regressions. It must not hide missing physics semantics with render-side animation or guessed assets.

## Current readiness

The important distinction is between infrastructure already running natively and retail-semantic gates that are still closed.

| Area | State | Notes |
| --- | --- | --- |
| Retail resource extraction / typed parsing | Ready for current slice | BFF Type 0/1/2 and X12d=2 supported; Type 3 still needs an external Oodle-compatible runtime |
| Silverstone scene reconstruction | Ready enough for slice integration | Scene placement, geometry, material/shader admission and native scene submission exist; ambiguous render semantics remain fail-closed |
| Native XCB/Vulkan runtime | Ready | Window, device/swapchain, indexed draws, scene submission, shaders, textures, state transport and validation-oriented paths are implemented |
| Continuous native session | Ready | Persistent runtime state, live input transport, camera state, physics state and Vulkan submission run in one session |
| BMW outer Vehicle -> VHF numeric relation | **Positive** | `SHIFT.BMWOuterVHFNumericRelation/1` |
| BMW BODY0 bind frame | **Positive** | `SHIFT.BMWBody0BindFrameProof/1` |
| Fresh persistent BMW world transform | **Positive** | `SHIFT.BMWPersistentWorldTransformRuntimeWiring/1`; production path is freshness-gated |
| Retail outer scheduler/cadence | **Positive and consumed** | `SHIFT.RetailOuterUpdateCadence/1` plus strict native outer-scheduler authority seam |
| Selected-session loaded inner physics rate | **Blocked — current shortest blocker** | Exact hash-locked `PhysicsTweaker` payload must be materialized and its unique `tick rate` admitted |
| Retail inner BODY substep execution | Blocked | Must consume the exact selected-session loaded `1/rate`; host pacing or constructor defaults cannot substitute |
| Retail vehicle/control producer chain | Incomplete | Deep producer/owner handoffs still need source-backed closure |
| Input -> drivetrain/wheel/control mapping | Incomplete | Live input exists, but full retail control consumption is not yet admitted |
| Retail camera follow | Incomplete | Camera transport exists; authoritative source/timing must follow the fresh admitted vehicle transform |
| End-to-end playable Linux slice | **Not yet** | Final integration remains gated by the items above |

## Current blocker: selected-session `PhysicsTweaker` rate

The BMW frame bridge, BODY0 bind, persistent world-transform wiring and retail outer cadence are already positive. The shortest remaining blocker is the exact **loaded inner physics tick rate** for the selected retail session.

The resource identity is locked:

```text
archive:       PHYSICSBOOTFLOW.bff
entry index:   49
entry path:    vehicles/physics/physicstweaker.xml
compression:   Type 2
archive SHA256:
  f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a
decoded SHA256:
  6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f
```

Dedicated materializer:

```text
tools/materialize_s5_selected_physics_tweaker_rate.py
```

The rate is admitted only when the decoded payload hash matches and exactly one valid `tick rate` property is present.

The constructor default of **180 Hz is not sufficient evidence** for the selected session because `PhysicsTweaker.xml` may override it. Host `1/60`, worker polling intervals, community defaults, or modded values cannot satisfy this gate.

Current machine-readable frontier:

```text
outer_vehicle_root_to_VHF_relation_numeric_matrix_ready = true
BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready    = true
BODY0_bind_frame_proof_ready                            = true
vehicle_world_transform_ready                           = true
retail_outer_cadence_admitted                           = true
retail_outer_authority_seam_ready                       = true

loaded_inner_physics_rate_admitted                      = false   <- CURRENT
retail_inner_substep_execution_admitted                 = false
retail_control_chain_complete                           = false
retail_camera_follow_ready                              = false
```

No original-game execution or runtime capture is currently required for this blocker; it is a resource-materialization/admission problem.

## Active blocker graph

```text
PROCESS 1
selected-session PhysicsTweaker tick-rate proof/admission
        |
        v
PROCESS 2
exact 1/rate persistent BODY inner substeps
        |
        v
PROCESS 1
missing vehicle-physics/control producer provenance
        |
        v
PROCESS 2
native producer/control consumption
        |
        v
PROCESS 1
input -> drivetrain/wheel/control mapping
        |
        v
PROCESS 2
continuous admitted control execution
        |
        v
PROCESS 1
retail camera-follow source + timing
        |
        +-----------------------------+
        |                             |
        v                             v
PROCESS 2                        PROCESS 3
fresh current vehicle           Silverstone + exact BMW
transform/camera feed           resource/bootstrap/Vulkan
        |                             |
        +--------------+--------------+
                       v
             native playable Linux slice
```

### Immediate queues

```text
PROCESS 1
P1.1  admit exact selected-session PhysicsTweaker rate
P1.2  close deepest missing vehicle-physics/control producers
P1.3  close input -> drivetrain/wheel/control producer mapping
P1.4  prove retail camera-follow source and timing

PROCESS 2
P2.1  keep rate/scheduler consumers fail-closed
P2.2  consume admitted inner rate as exact persistent substep timing
P2.3  internalize positive producer/control handoffs
P2.4  publish a fresh current vehicle transform every admitted tick
P2.5  feed the admitted current transform into camera integration

PROCESS 3
P3.1  keep exact Silverstone + BMW resource bootstrap runnable
P3.2  preserve exact BMW VHF identity without basename fallback
P3.3  consume freshness-gated Process 2 vehicle transforms
P3.4  keep the Vulkan slice green and fix only slice-blocking render/resource regressions
```

A downstream process may build the immediate fail-closed consumer seam for the next expected handoff, but it may not guess an unresolved upstream semantic value just to stay busy.

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

The Silverstone Era3 dependency surface is structurally reconstructed far enough for the current vertical-slice path. Unsupported shader/resource choices remain explicit blockers rather than being guessed.

The BMW scene path consumes the exact canonical render model:

```text
vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

Static VHF object-frame transport is kept separate from dynamic vehicle pose.

### BMW frame and world-transform proof

The earlier render/physics frame blocker is closed.

Positive contracts include:

- retail BMW chassis BODY index `0` identity;
- BODY0 resource/local -> SDF bind facts;
- selected-session BODY0 -> outer Vehicle numeric relation;
- `SHIFT.BMWVehicleRenderModelResourceJoin/1`;
- `SHIFT.BMWVHFHierarchyRootFrame/1`;
- `SHIFT.OuterVehicleRenderSnapshotAffineBridge/1`;
- `SHIFT.OuterVehicleRenderRootDeltaProvenance/1`;
- `SHIFT.VehicleRenderModelRootAffineDomainJoin/1`;
- `SHIFT.OuterVehicleBMWVHFRootRelation/1`;
- `SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1`;
- `SHIFT.BMWOuterVHFNumericRelation/1`;
- `SHIFT.BMWBody0BindFrameProof/1`;
- `SHIFT.BMWPersistentWorldTransformRuntimeWiring/1`;
- `SHIFT.BMWVHFRootFrameSceneConsumer/1`.

For the first explicit native primary-player bootstrap:

```text
delta_local = outerVehicle[+0x19c,+0x1a0,+0x1a4]
            = (0, 0, 0)

producer    = FUN_00795d60
lifetime    = Vehicle::InitVehicle setup state
role        = primary-player / Vehicle+0x234 == 0
```

That proof is deliberately narrow and is not generalized to other roles, restart states, or origin transitions without evidence.

### Native Vulkan renderer

Implemented renderer infrastructure includes:

- XCB window creation;
- Vulkan instance/device/surface/swapchain setup;
- indexed multi-draw submission;
- neutral scene-set execution;
- semantic-aware affine transforms;
- SPIR-V shader loading;
- constant-buffer transport;
- 2D textures and supported cube resources;
- per-draw cull/depth/blend state for the proven material subset;
- validation-oriented regression paths;
- freshness-gated persistent vehicle transform upload.

The renderer transport is no longer the main blocker for authentic vehicle motion. Current gating work is upstream in retail physics/control semantics.

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

- BODY accumulator helpers;
- JOINT/HINGE/BAR projection and matrix-coupling kernels;
- generated BODY constraint/matrix assembly;
- builtin diagonal reset and sparse solve execution;
- post-solve BODY projection;
- BODY point transforms;
- wheel/contact response arithmetic;
- auxiliary contact-response chaining;
- source-backed wheel-force aggregation;
- persistent BODY pose storage and generation/freshness checks;
- strict scheduler-authority admission seams;
- persistent BMW world-transform publication.

This is still **not a complete retail vehicle frame**. The selected loaded inner rate, remaining producers and control chain must be admitted before the native loop can claim retail-consistent continuous vehicle execution.

### Input and camera

Already implemented:

- live X11 keyboard control intent;
- deterministic scripted input for regression tests;
- recovered CameraManager state transport;
- guarded camera double-buffer updates;
- camera state carried inside the continuous native session.

Still missing:

- exact retail input/control producer mapping into drivetrain/wheel state;
- continuous consumption of that proven control chain;
- authoritative camera-follow source and timing tied to the current admitted vehicle transform.

### Continuous runtime

The Linux runtime is already an integrated persistent execution shell rather than a one-frame renderer test:

```text
resource-backed scene
  + native runtime state
  + input
  + camera state
  + physics packets/state
  + persistent BMW state
  -> continuous native session
  -> Vulkan frame submission
```

`--continuous` uses host wall-clock pacing. Host pacing is an execution policy, not retail scheduler evidence. Retail outer cadence is independently proven; retail inner substep timing remains gated on the exact loaded `PhysicsTweaker` rate.

## Evidence policy

The repository deliberately stays fail-closed.

- Static executable evidence, runtime observations and resource identity remain separate until explicitly joined.
- Callgraph proximity is not ownership.
- Equal numeric values are not provenance.
- Visual similarity is not resource identity.
- Identity-valued matrices do not prove identity semantics.
- Static VHF transforms are not dynamic vehicle pose.
- Missing proof remains a blocker instead of being guessed.
- Runtime-owned renderer resources are not silently synthesized.
- Native execution requires explicit provenance/admission gates.
- Host pacing cannot stand in for retail scheduler evidence.
- Fixtures and test scripts cannot satisfy retail-semantic gates.
- A native implementation is not automatically treated as recovered retail behavior.

Common evidence states:

```text
proven
verified
inferred
ambiguous
unknown
unsupported
blocked
```

Cross-process handoffs should be versioned machine-readable contracts when practical:

```text
SHIFT.<Name>/1
```

## Ghidra evidence database

Static analysis is exported into machine-readable evidence instead of remaining only inside an interactive Ghidra project. The database contains functions, callgraph edges, strings/xrefs, globals, static data, switch candidates, factory candidates, constructors and vtable candidates.

Typical export:

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_shift_export.sh \
  /path/to/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/shift_ghidra_database
```

Targeted instruction/p-code exports are used when a blocker needs exact register/value/store provenance instead of broad decompiler output.

The current exported database for `SHIFT.exe` is built around a 32-bit x86 PE and contains machine-readable functions, call edges, strings, candidate vtables/constructors, globals, static tables, switches and factory candidates.

## Runtime evidence

Static analysis cannot uniquely recover every runtime identity. The repository therefore also contains bounded retail capture/audit paths.

### D3D9 capture

`native_capture/` and `src/graphics/d3d9/` cover:

- tied FXO permutations;
- draw-local texture/resource identity;
- Silverstone IMB draw attribution;
- runtime transforms;
- same-instance shader/resource proof;
- renderer-owned resources.

### Physics/runtime capture

`tools/` contains bounded runtime probes, evidence packaging and verification helpers for provider behavior that cannot be recovered uniquely from static code.

Runtime capture should only be requested when the exact current blocker cannot be closed from static/resource evidence.

## Native vertical-slice launcher

The integration runner consumes one profile instead of a long manually assembled command line:

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

A valid launch profile confirms structural/runtime contracts; it does not by itself prove gameplay semantics.

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

Those are outside the current blocker graph. Android remains deferred until the desktop/native runtime boundary is stable.

## Definition of the first playable slice

The milestone is reached only when one continuous native session satisfies all of the following:

```text
[ ] authentic Silverstone resources loaded
[ ] real retail BMW instantiated from exact resources
[ ] user input reaches source-backed control producers
[ ] physics executes continuously with persistent state
[ ] retail outer cadence and selected-session inner rate are admitted
[ ] BODY0 continuously produces a fresh admitted vehicle world transform
[ ] camera follows the proven current vehicle source/timing
[ ] Vulkan renders Silverstone + BMW continuously
[ ] no test-only transform script drives core vehicle motion
[ ] no unsupported semantic guess is required for the core loop
```

Until every item is true, the repository should be described as an **advanced decompilation/reconstruction with a functioning native Linux runtime skeleton and multiple closed vehicle/render integration proofs**, not as a finished native port.
