# Need for Speed: SHIFT — decompilation and native Linux reimplementation

Evidence-driven reconstruction of *Need for Speed: SHIFT* file formats, runtime contracts and game systems, with an offline native Linux/Vulkan runtime as the primary execution target.

**Mainline checkpoint: Phase 660.**

This repository is no longer only a resource extractor. It contains a connected reconstruction of the resource pipeline, scene/track data, renderer contracts, camera/input state, vehicle physics and a native Linux runtime shell. The project is **not yet a complete playable native build**: several runtime joins still require authentic retail evidence before they can be implemented without guessing.

The current vertical-slice target is straightforward:

```text
retail SHIFT resources
  → verified extraction / analysis
  → evidence-backed neutral IR
  → Silverstone scene + real vehicle
  → Vulkan renderer + native physics
  → offline Linux runtime
```

## Project scope

The target is an offline native runtime for the original game content. The Linux test build intentionally does **not** depend on:

- EA services;
- DRM;
- login/profile/cloud services;
- matchmaking or online networking;
- Bink/video playback.

Those systems are outside the current decompilation target.

## Evidence policy

The project is deliberately fail-closed.

- Static executable/source evidence, runtime observations and reconstructed contracts are kept separate.
- Ambiguous values remain ambiguous.
- Missing evidence is represented as a blocker instead of being guessed.
- Different retail formats may feed the same neutral runtime contract without being declared identical.
- Native execution requires explicit provenance/admission gates in addition to structurally valid data.
- Runtime-owned renderer resources are never silently synthesized.

Common evidence states include `proven`, `verified`, `inferred`, `ambiguous`, `unknown`, `unsupported` and `blocked`.

This policy is important: the goal is not merely to make something that resembles SHIFT, but to reconstruct the original behavior as far as the available evidence allows.

## Architecture

### Resource pipeline

```text
BFF
  → extraction / decompression / hashes
  → typed format analysis
  → neutral resource IR
  → scene / render / physics contracts
```

The active corpus supports SHIFT BFF Type 0/1/2 extraction and X12d=2 encryption. Type 3 still depends on an externally supplied Oodle-compatible runtime.

The main analysis/orchestration entry point is:

```bash
python shift_importer.py --help
```

BFF-specific usage is documented in [`BFF_TOOLS.md`](BFF_TOOLS.md).

### Render pipeline

```text
BFF
  → MEB / IMB / IMX / BMT / DDS / FX / FXO
  → DrawPacket
  → StaticDraw
  → RenderCommand
  → Vulkan artifacts
  → native runtime
```

Two important render paths currently converge on this boundary:

- **BMW/MEB** — the long-running material, shader, DDS and Vulkan regression slice;
- **SGB/MeshInst** — track-scene geometry through source-backed IMB binary and IMX XML adapters.

The renderer keeps resource identity and provenance explicit all the way to native submission. The desktop/reference path is used as an oracle where appropriate; Vulkan is the native backend direction.

### Scene / Silverstone pipeline

```text
SGB
  → NODE / SUMM / PART / FLAT / OBJECT
  → scene placement
  → MeshInst resource resolution
  → IMB / IMX neutral geometry
  → material + shader binding
  → runtime evidence admission
  → NativeSceneBundle
  → NativeSceneVulkanSet
  → native execution
```

The static Silverstone Era3 dependency surface is extensively reconstructed. The remaining hard boundary is not basic parsing: it is exact runtime identity for tied shader/resource choices, renderer-owned resources, some transform history and higher-level streaming/LOD behavior.

Runtime D3D9 capture tooling exists specifically to close those ambiguities without selecting a candidate heuristically.

### Vehicle physics pipeline

```text
CDF + EDF + GDF + SDF
  → VehiclePhysicsAssetGraph
  → participant / selector boundaries
  → BODY + JOINT / HINGE / BAR state
  → matrix / RHS assembly
  → reset / sparse solve
  → post-solve projection
  → wheel / contact response primitives
  → native fixed-step runtime
```

A substantial part of the pre-PhysX / SDF numerical path has been reconstructed and ported to native C++.

Recent native work includes:

- BODY accumulator helpers;
- JOINT/HINGE/BAR projection and matrix-coupling kernels;
- generated BODY constraint/matrix assembly;
- builtin reset + sparse solve execution;
- post-solve BODY projection;
- wheel-contact response arithmetic;
- BODY point transforms;
- auxiliary contact-response chaining;
- the Phase 660 three-record `FUN_00759c90` wheel-force aggregate.

These are source-backed arithmetic/runtime primitives. They do **not** yet imply a complete retail vehicle simulation. Important caller-side scheduling, per-frame state producers, persistent BODY pose/motion integration and provider-present execution remain separate gates.

## Native Linux runtime

`native_runtime/` contains the current offline runtime shell:

```text
prepared render / physics IR
  → XCB window
  → Vulkan surface + swapchain
  → material / scene draw submission
  → fixed 60 Hz runtime state boundary
```

Current capabilities include:

- XCB/Vulkan window and swapchain setup;
- prepared single- and multi-draw material execution;
- neutral scene-set execution;
- semantic-aware affine scene transforms;
- constant-buffer and texture packet consumption;
- explicit 2D texture and supported cube-resource transport;
- validation-oriented Vulkan execution paths;
- fixed 60 Hz native ticks;
- live keyboard control intent;
- deterministic input scripts for regression testing;
- recovered camera-state transport and guarded buffer updates;
- physics participant/workspace admission;
- source-backed native solver, constraint and wheel/contact primitives;
- JSON telemetry used by CI and regression checks.

The native runtime is currently a reconstruction/test shell, not the finished game loop. It intentionally stops when the next behavior would require unsupported assumptions.

## Current status

| Area | State | Main open boundary |
|---|---|---|
| BFF / XMem-LZX | verified for the active corpus | uncommon variants; external Type 3 codec |
| Resource IR | active and broadly connected | remaining format-specific joins |
| MEB / vertex ABI | strong coverage | additional runtime/same-instance proof where needed |
| IMB / IMX MeshInst | source-backed adapters implemented | broader variants and runtime identity proof |
| BMT / material state | source-backed subset | remaining alpha-test/bias/stencil and global state |
| FX / FXO | parser + attribution pipeline implemented | authentic runtime selection for tied permutations |
| Silverstone / SGB | strong structural and render handoff | exact runtime shader/resources, transform history, streaming/LOD |
| Vulkan | active native backend | remaining D3D9 parity and renderer-owned resource coverage |
| Camera | native state bridge active | exact retail update timing/controller/view integration |
| Input | X11 keyboard + deterministic scripts | retail analog/gamepad filtering semantics |
| AI / track | source-backed core present | remaining linked/local runtime search behavior |
| Vehicle physics | deep structural/numeric reconstruction through Phase 660 | full per-frame producers/scheduling, persistent motion, provider-present path |
| Native runtime | working offline XCB/Vulkan shell | complete resource-driven game loop and vertical-slice integration |
| Android | deferred | waits for a stable desktop/native runtime boundary |

## What still blocks a playable Linux vertical slice

The largest remaining integration boundaries are:

1. **Exact scene rendering from authentic runtime evidence.** Silverstone parsing and scene handoff are well advanced, but tied shader choices and some renderer-owned resources still need exact D3D9 observations.
2. **Complete vehicle state evolution.** Many solver/contact kernels are native, but the project still needs the proven per-frame producers, scheduling and persistent BODY/vehicle pose integration that turn those kernels into continuous vehicle motion.
3. **Remaining surface/contact outer logic.** Phase 660 provides a native wheel-force aggregate, while larger surrounding response/scheduling paths remain separate reconstruction targets.
4. **Provider-present physics execution.** The provider capture/verification tooling exists, but exact retail provider numerical behavior still requires authentic runtime evidence.
5. **Runtime orchestration.** The bounded reconstruction shell must ultimately become a resource-driven game loop that connects scene loading, vehicle creation, camera, controls, simulation and rendering without test-only handoff files.

These boundaries are intentionally independent. Closing one does not authorize guessing another.

## Build and test

### Python environment

Python 3.9+ is required by the repository bootstrap script.

```bash
./install_requirements.sh
source .venv/bin/activate
```

Run the main Python regression suite:

```bash
python -m pytest -q
```

Run the live-memory tooling tests:

```bash
make -C tools/shift_live_dump test
```

### Native Linux runtime

The native runtime requires Vulkan, XCB and `glslangValidator` at configure/build time.

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

Linux CI exercises software Vulkan/lavapipe paths, shader compilation/reflection, validation checks, material/scene submission and focused native-physics regressions.

## Runtime evidence tooling

Some behavior cannot be recovered uniquely from static analysis. The repository therefore contains dedicated capture paths for retail execution.

### D3D9 capture

`native_capture/` and `src/graphics/d3d9/` contain capture/audit/attribution tooling used to connect actual retail draw calls to reconstructed resources, shaders, constants and external textures.

This is used for cases such as:

- tied FXO permutations;
- Silverstone IMB draw attribution;
- same-instance shader/resource proof;
- draw-local texture snapshots;
- runtime transform evidence.

### GDB / WineDbg physics capture

`tools/` contains bounded SDF/runtime probes, evidence packaging, verification and replay tooling for behavior that is only observable in a live retail process.

The capture pipeline is designed so that incomplete or mixed-session evidence remains blocked instead of being silently promoted.

## Repository map

| Path | Purpose |
|---|---|
| `shift_importer.py` | primary importer / analysis / orchestration CLI |
| `src/formats/` | resource, material, geometry and collision parsers |
| `src/graphics/d3d9/` | D3D9 capture, PE and renderer evidence tooling |
| `src/render/` | neutral render contracts and reference rendering logic |
| `src/render/vulkan/` | Vulkan packet/bundle preparation |
| `src/scene/` | SGB, MeshInst, IMB/IMX and native-scene contracts |
| `src/physics/` | reconstructed vehicle/solver/runtime physics contracts |
| `src/track/` | track metadata and runtime query contracts |
| `src/bmw/` | BMW M3 E36 regression and retail render path |
| `native_ir/` | shared native intermediate representation support |
| `native_vulkan/` | native Vulkan checks/executors |
| `native_runtime/` | offline Linux XCB/Vulkan runtime and native physics |
| `native_capture/` | native D3D9 capture producer |
| `tools/` | Ghidra, capture, audit, trace and evidence utilities |
| `evidence/` | checked-in derived evidence and manifests |
| `tests/` | Python regression suite |
| `docs/status/` | subsystem status notes |
| `docs/PHASE*.md` | detailed chronological reconstruction record |

## Documentation strategy

The README describes the current architecture and the shortest path to a native Linux vertical slice. Detailed historical evidence is intentionally kept elsewhere:

- [`ROADMAP.md`](ROADMAP.md) — long-form execution history and backlog;
- [`docs/status/`](docs/status/) — subsystem-specific operational notes;
- `docs/PHASE*.md` — evidence and implementation record for individual phases;
- [`NOTICE.md`](NOTICE.md) — repository notice and project context.

When a phase note and a newer implementation disagree, the newer source/tests and current subsystem status are authoritative. Historical phase files are preserved rather than rewritten retroactively.

## Development direction

The practical order of work is:

```text
close missing retail evidence
  → finish native scene/resource admission
  → finish persistent vehicle-state integration
  → connect the real vehicle + Silverstone to native runtime
  → replace bounded test orchestration with the game loop
  → broaden renderer/physics/AI coverage
```

The immediate goal is not to reproduce online services or peripheral middleware. It is to reach a deterministic, evidence-backed offline Linux build that can load authentic retail content, render a real track/vehicle and execute the reconstructed simulation natively.
