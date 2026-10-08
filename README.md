# Need for Speed: SHIFT — decompilation and native Linux runtime

Evidence-driven reconstruction of *Need for Speed: SHIFT* with one practical milestone: a native offline Linux/Vulkan playable slice driven by original retail resources.

The repository already contains a connected retail-resource pipeline, Silverstone scene reconstruction, native Vulkan execution, a continuous runtime shell, persistent BMW physics state, retail scheduler/timing evidence, a proven BMW render/physics frame bridge, and progressively internalized vehicle-physics behavior.

It is **not yet a complete playable native build**. The project deliberately prioritizes the shortest evidence-backed path to the first Silverstone + BMW M3 E36 playable slice instead of attempting to decompile every `SHIFT.exe` function first.

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

## Live project status

Do **not** use phase notes, old PR descriptions, or this README as a live task queue.

The machine-readable source of truth is:

- [`evidence/playable_slice_three_process_execution.json`](evidence/playable_slice_three_process_execution.json)

The human-readable status, blocker burndown, active lanes, provider count and parallel-ready work are generated from it:

- [`coordination/PLAYABLE_SLICE_STATUS.md`](coordination/PLAYABLE_SLICE_STATUS.md)

Development ownership and merge rules are defined in:

- [`coordination/DEVELOPMENT_PROCESS_V2.md`](coordination/DEVELOPMENT_PROCESS_V2.md)
- [`coordination/lane_ownership.json`](coordination/lane_ownership.json)
- [`PROCESS_INSTRUCTIONS.md`](PROCESS_INSTRUCTIONS.md)

Before substantial work, answer:

> **Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

## Development model

The playable slice keeps three semantic ownership domains while exposing the real parallel lanes explicitly:

```text
P1A-contact   retail contact/collision proof
P1B-control   retail input/control provenance
P1D-camera    retail camera-follow provenance
       |
       v
P2-runtime    native physics/runtime consumption
       |
       v
P3-integration resources / scene / Vulkan / bootstrap
       |
       v
native playable Linux vertical slice
```

Processes exchange only explicit fail-closed contracts. Missing semantic ownership is never guessed or transferred merely to keep another lane busy.

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

The selected BMW render path uses the retail model:

```text
vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

Static VHF object-frame transport remains separate from dynamic vehicle pose.

### Persistent vehicle runtime

The native source-backed path contains substantial pre-PhysX / SDF numerical and vehicle-runtime infrastructure:

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

Closed infrastructure includes persistent BMW BODY state, freshness-gated world-transform publication, selected-session scheduler timing, exact fixed inner execution, source-backed solver kernels, BODY projections, wheel/contact arithmetic, and multiple recovered collision/contact-response paths.

The current provider count and exact remaining native boundaries are intentionally **not duplicated here**; use the generated status page so this README cannot drift from `main`.

### Input and camera transport

Already implemented infrastructure includes live X11 keyboard intent, deterministic scripted input for regressions, CameraManager state transport, guarded camera double-buffer updates, and camera state inside the continuous native session.

Retail-semantic completion of control and camera-follow remains governed by the canonical execution gates, not by the existence of transport code.

### Continuous runtime

The Linux runtime is an integrated persistent execution shell rather than a one-frame renderer test:

```text
resource-backed scene
  + native runtime state
  + input
  + camera state
  + persistent BMW physics state
  + admitted retail timing
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

Launch after the canonical profile/runtime gates are ready:

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

Authoritative external research-input identities and hashes are centralized in [`coordination/research_inputs.lock.json`](coordination/research_inputs.lock.json). A Drive folder, filename, Ghidra index or decompiler output is not semantic authority merely because it exists.

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

CI uses stable coordination/evidence/full/native/Vulkan gates. New development should add pytest/CTest targets or matrix entries instead of creating another phase-numbered workflow. Historical phase documents remain evidence/history and do not select current work.
