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

Processes exchange only explicit fail-closed contracts. Missing semantic ownership is never guessed. When a large proof frontier is explicitly sharded, aggregate queue ownership stays with its integration owner while bounded shard work may be executed by the other P1 lanes under `coordination/lane_ownership.json`.

### Current process snapshot — 2026-10-09

This is a convenience snapshot only. The execution JSON and generated status above remain authoritative if this section ever drifts.

- **Process 1A / P1A-contact:** P1.1 `FUN_00766510/contact_response` proof and P1.2 `FUN_00765c40` ownership proof are complete. In addition, P1A now owns shard **P1.3A**: computed `manager+0x374` paths `0x005292db` and `0x005f4ffa`, plus selected-root provenance for `HDVehicle+0x938` and `HDVehicle+0x13b8`.
- **Process 1B / P1B-control:** P1B remains the aggregate P1.3 integration owner but now carries only shard **P1.3B**: computed paths `0x005f6eda` and `0x0070f62d`, the final `manager+0x374 -> HDVehicle+0x4330` identity join, and final `0x004b86cf` / slot2 adjudication. It integrates P1.3A/P1.3B/P1.3D into the final handoff for P2.6.
- **Process 1D / P1D-camera:** P1.4 retail camera-follow provenance is complete. P1D now additionally owns shard **P1.3D**: computed paths `0x0070fb45` and `0x0070fdeb`, selected-root provenance for `HDVehicle+0x28b8`, and the remaining indirect/native APC injection timing closure for the Controller #1 alertable-worker producer chain.
- **Process 2 / P2-runtime:** P2.3 may now consume the complete `contact_response` handoff; provider count stays at **7** until the external boundary is actually gone. In P2.4, the `FUN_007584f0 -> 0x00783a30` interpolation helper path and `FUN_0075cfb0` commit surface are native-owned, while two positive-load qword producers and wheel-job producer arithmetic/branch predicates remain open. P2.6 remains blocked until the three P1.3 shards are integrated.
- **Process 3 / P3-integration:** resource, Silverstone/BMW scene, launcher and Vulkan infrastructure are maintained continuously. Final continuous presentation remains blocked on the completed retail control chain and a Process 2 runtime camera feed.

P1.3 is therefore balanced as **4 work items per P1 lane**: two computed forwarding paths plus two additional provenance/timing items for P1A, P1B and P1D respectively. The current external vehicle-provider count is **7**. The first planned architectural reduction remains `FUN_00766510/contact_response`: **7 -> 6** only after Process 2 removes that boundary from selected production execution.

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

The current provider count and exact remaining native boundaries are intentionally summarized only in the dated snapshot above; use the generated status page and execution JSON for authoritative live state.

### Input and camera transport

Already implemented infrastructure includes live X11 keyboard intent, deterministic scripted input for regressions, CameraManager state transport, guarded camera double-buffer updates, and camera state inside the continuous native session.

Retail camera-follow provenance is now complete. Runtime camera-feed production/consumption remains a separate Process 2 -> Process 3 gate. Retail-semantic control completion remains governed by the integrated P1.3 result rather than by the existence of input transport code.

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
