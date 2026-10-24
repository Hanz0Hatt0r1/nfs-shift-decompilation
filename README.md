# Need for Speed: SHIFT — Android port research and native runtime

Evidence-driven reconstruction and recompilation of **Need for Speed: SHIFT (PC retail 1.02)**, targeting a native **Android/ARM64 port**. Linux with Vulkan is the bring-up and debugging platform used to advance the same portable runtime toward Android.

The project is **not playable yet**, but it has moved well beyond isolated function recovery. The complete frozen PC instruction corpus can now be lowered to native C, linked into a Linux ELF module, loaded beside the original PE32 image, and executed through a growing Win32 guest-runtime bridge inside the Vulkan runtime.

## Current status — 2026-10-19

| Area | Status |
| --- | --- |
| Frozen PC function corpus discovered | **41,538 functions** |
| P-code lowering coverage | **41,538 / 41,538 functions (100%)** |
| Covered machine instructions | **2,088,152 / 2,088,152** |
| Covered P-code operations | **9,600,713** |
| Linux native module | **Links and exports all 41,538 lowered functions** |
| Original `SHIFT.exe` PE32 loading | **Implemented** |
| PE32 entry-point execution | **Implemented** |
| Guest x86 RAM/register/TEB state | **Implemented for current startup needs** |
| Import/IAT dispatch | **Implemented, bounded subset of Win32 APIs** |
| Retail startup probe | **v114 reaches 342,703 guest dispatches / 1,417 unique functions and renders 1,800 Vulkan frames with validation enabled and zero errors; the recent function history is unchanged from v113** |
| Native Vulkan runtime | **Operational** |
| Retail resource pipeline | **Operational** |
| Silverstone + BMW native scene path | **Operational as reconstruction infrastructure** |
| Full retail game startup | **Not complete** |
| Menu / race / playable game | **Not complete** |
| Behavioral parity | **Not proven** |

The most important distinction is:

> **100% P-code lowering coverage does not mean 100% game reconstruction.**

All functions in the frozen instruction corpus can be converted into native host code, but the original executable still depends on Windows process/thread behavior, imported APIs, runtime state, scheduling, graphics integration, exception handling, and game-specific initialization that must be reproduced or replaced correctly.

## What runs today

The current recompilation path is:

```text
PC retail SHIFT.exe
        |
        v
PE32 guest image loader
        |
        +--> original image mapped at preferred ImageBase
        +--> sections / virtual tails
        +--> import table -> guest IAT traps
        +--> x86 register bank / sparse 4 GiB guest RAM
        +--> TEB / FS base / initial x87 state
        |
        v
lowered P-code functions
        |
        +--> 41,538 native host exports
        +--> direct / computed calls
        +--> memory callbacks
        +--> x86 userops
        |
        v
native Linux runtime
        |
        +--> guest Win32 compatibility services
        +--> fixed-step execution
        +--> resource-backed scene state
        +--> XCB + Vulkan frame loop
```

The retail PE entry point has been executed against the real **PC retail 1.02** image with the freshly rebuilt 41,538-export P-code module, cooperative guest scheduler, 32 startup supplements and Linux runtime. Probe v114 runs **342,703 guest dispatches across 1,417 unique functions** and renders 1,800 Vulkan frames with validation enabled and zero errors. Its 64-entry main-thread history and final stack are identical to v113: the stack ends at `0x006472d0`, with four workers waiting. The longer run added no new unique functions. Static analysis identifies `FUN_0040ba50` as an exit-controlled app loop, so the entry point staying active is expected; the guest still has not demonstrated the frontend or a retail draw on the Linux renderer. The history reaches the `0x0050ceb0` state gate and the `0x00833670` callback sequence; field meanings remain under analysis. The renderer uses converted MGEO smoke geometry, so this is not retail D3D9 rendering or a playable session. The regenerated multi-gigabyte P-code sources, object shards and ELF remain in the external artifact cache; their hashes and build inputs are recorded in [full-module rebuild evidence](evidence/pcode_full_linux_rebuild_20261018.json). Probe details are in the [v114 record](evidence/retail_frontier_20261019/entrypoint_probe_v114.json) and [captured log](evidence/retail_frontier_20261019/shift-probe-v114-function-history-1800-validation.log). Historical v65-v67 probes also traced a 254,529,224-byte allocator request through `0x00886900` to `FUN_0062f2d0`; see the [request-origin analysis](evidence/recompiled_pcode_android_retail_frontier_v67_pool_request_origin_20261018.md). The retail data directory is available in the PortProton prefix at `/home/pes/PortProton/data/prefixes/DEFAULT/drive_c/GOG Games/Need For Speed.Shift.v 1.02`; its `SHIFT.exe` matches the analyzed PE by SHA-256.

This is a startup/recompilation frontier, not a completed entry point or playable-game result. The project target and current priorities are defined in [`ROADMAP.md`](ROADMAP.md).

See:

- [`docs/PROCESS_0_PCODE_NATIVE_LOWERING.md`](docs/PROCESS_0_PCODE_NATIVE_LOWERING.md)
- [`docs/RECOMPILED_PCODE_VULKAN_PE32_LOADER.md`](docs/RECOMPILED_PCODE_VULKAN_PE32_LOADER.md)
- [`evidence/pcode_native_lowering_coverage_full_20261018.json`](evidence/pcode_native_lowering_coverage_full_20261018.json)
- [`evidence/recompiled_pcode_pe32_fiber_memory_frontier_20261018.json`](evidence/recompiled_pcode_pe32_fiber_memory_frontier_20261018.json)
- [`evidence/recompiled_pcode_android_retail_frontier_20261018.json`](evidence/recompiled_pcode_android_retail_frontier_20261018.json)
- [`evidence/pcode_full_linux_rebuild_20261018.json`](evidence/pcode_full_linux_rebuild_20261018.json)
- [`evidence/retail_frontier_20261019/entrypoint_probe_v114.json`](evidence/retail_frontier_20261019/entrypoint_probe_v114.json)
- [`evidence/retail_frontier_20261019/entrypoint_probe_v113.json`](evidence/retail_frontier_20261019/entrypoint_probe_v113.json)
- [`evidence/retail_frontier_20261018/entrypoint_probe_v112.json`](evidence/retail_frontier_20261018/entrypoint_probe_v112.json)

## Full frozen-corpus recompilation

The repository contains a generic, fail-closed lowering path for the PC retail x86 P-code corpus.

The current pinned corpus contains:

```text
41,538 functions
2,088,152 machine instructions
9,600,713 P-code operations
```

All **41,538 functions are lowerable**. The generated C is compiled into bounded object shards and linked into a 64-bit Linux ELF shared object that exports the lowered guest functions as `rvi_XXXXXXXX` symbols.

The generated multi-gigabyte sources, object files and linked modules are intentionally kept outside Git. The repository stores the scripts, hashes, manifests and evidence required to reproduce and verify them.

This closes the **frozen-corpus code-generation problem**. It does not close:

- missing functions outside the frozen exported corpus or functions that require supplemental recovery;
- Windows platform/runtime behavior;
- complete process, thread and fiber semantics;
- structured exception handling;
- all imported DLL services;
- retail initialization and scheduler behavior;
- graphics/API equivalence;
- behavioral parity with the original executable.

## PE32 guest runtime

`shift_runtime` can map the original x86 PE32 executable into guest memory and invoke its entry point through the recompiled function bridge.

Implemented infrastructure includes:

- DOS/PE/I386/PE32 validation;
- preferred-base image mapping;
- section loading and zero-filled virtual tails;
- import-table parsing and IAT trap rewriting;
- sparse guest memory and x86 register state;
- initialized FS base and minimal x86 TEB;
- initialized x87 control/status/tag state;
- supplemental P-code ELF modules;
- direct, computed and import-thunk dispatch;
- selected x86 userops such as CPUID and RDTSC;
- a growing single-thread Win32 compatibility layer.

The implemented Win32 surface already covers a substantial startup subset including process/thread identity, timing, heap and virtual memory, TLS, critical sections, events, mutexes, files, environment/code-page helpers, WinMM timer-period calls, basic fiber identity, local time and memory-status queries.

The layer remains deliberately **fail-closed**: an unsupported API, impossible guest state or missing generated function stops execution instead of silently inventing behavior.

## What is still blocking retail startup

The project is currently in the stage of extending the real retail entry-point execution frontier.

Major remaining classes of work include:

1. recovering or supplementing missing guest function exports encountered by retail startup;
2. implementing additional imported Win32 APIs only when the retail execution path proves they are required;
3. completing process/thread/fiber behavior beyond the current single-thread model;
4. implementing exception behavior where retail startup actually depends on it;
5. reproducing the required scheduler/timing semantics;
6. connecting original game-side graphics behavior to the native Vulkan renderer;
7. continuing execution far enough to initialize game systems, resources, UI and race state;
8. validating behavior against PC retail evidence rather than treating successful execution as semantic parity.

The runtime is therefore an **execution bridge and reconstruction platform**, not a Wine replacement and not yet a complete game port.

## Native resource and Vulkan path

In parallel with whole-program recompilation, the repository contains a native reconstruction path for original game resources.

```text
BFF
  -> extraction / decompression / hashes
  -> typed format analysis
  -> neutral resource IR
  -> scene / render / physics contracts
  -> native runtime assets
  -> Vulkan execution
```

The Silverstone/BMW path currently includes:

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
  -> Vulkan
```

The selected retail BMW model is:

```text
vehicles/bmw_m3_e36/bmw_m3_e36.vhf
```

Main importer entry point:

```bash
python shift_importer.py --help
```

BFF-specific tooling is documented in [`BFF_TOOLS.md`](BFF_TOOLS.md).

## Evidence-driven native playable slice

The repository also retains the earlier hand-reconstructed native vertical-slice program:

```text
Silverstone
+
retail BMW M3 E36
+
resource-driven bootstrap
+
input
+
persistent physics
+
fresh vehicle transform
+
camera
+
Vulkan
=
native playable Linux vertical slice
```

That track is still incomplete. Its coordination state is maintained separately from the newer whole-program P-code/runtime work.

Canonical files for that track:

- [`evidence/playable_slice_three_process_execution.json`](evidence/playable_slice_three_process_execution.json)
- [`coordination/PLAYABLE_SLICE_STATUS.md`](coordination/PLAYABLE_SLICE_STATUS.md)
- [`coordination/DEVELOPMENT_PROCESS_V2.md`](coordination/DEVELOPMENT_PROCESS_V2.md)
- [`coordination/lane_ownership.json`](coordination/lane_ownership.json)

At its current recorded frontier, the native slice still has an open retail control chain, an incomplete runtime camera handoff and external vehicle-provider boundaries. Its final playable smoke test is prepared but not runnable.

The recompilation path and the native vertical-slice path are complementary:

- the **P-code path** maximizes executable coverage and lets the original retail control flow run against a reconstructed platform layer;
- the **native slice path** isolates and replaces selected systems with evidence-backed native implementations.

Neither path is currently a complete playable game.

### Xbox retail PM4 to Vulkan frontend (Process 2)

The separate `shift-native` ReXGlue plugin consumes the Xbox guest PM4 ring and submits captured draws to the project-owned Vulkan 1.1 renderer. It is built without mapping `rexgpu-xenos`; the renderer core remains free of XCB/Wayland surface calls. The 2026-10-23 live run captured 100 `DRAW_INDX_2` packets (96 one-index AutoIndex point-list and four three-index AutoIndex rectangle-list). The plugin submitted 24 point draws and one rectangle draw at each of two guest swaps; it rejected the other rectangle variant because its captured state is `mode=6/color=0`. A debug magenta fragment override produced rasterized pixels ([diagnostic readback](evidence/process2_xbox_live_vulkan_magenta_raster_diagnostic_20261023.png)), while the captured retail pixel shader produced black readback ([native shader output](evidence/process2_xbox_live_vulkan_output_readback_black_20261023.png)). The live frontend therefore submits original retail draws, but visible game output and scene parity remain unverified. See the [live ring evidence](evidence/process2_xbox_live_guest_ring_20261023.json).

The 2026-10-24 Android rebuild on Redmi Note 8 Pro now dispatches the guest source-0/VBlank callback at 60 Hz. Its runtime log records two guest swaps, two Vulkan frame submissions, and a fully black readback and screenshot; no additional PM4 batches appeared during the next 170 seconds. VBlank delivery is therefore confirmed, while visible retail output and progress beyond those startup batches remain unverified. See the [VBlank probe](evidence/process2_redmi_note8pro_vblank_probe_20261024.json).

## Validation

The repository records reproducible evidence instead of treating local success as proof.

Recent recorded validation includes:

- **41,538 / 41,538** frozen functions lowerable;
- Linux ELF exports for the full lowered corpus;
- native runtime build passing;
- **138 / 138** native runtime CTests passing at the current PE32 startup frontier;
- Linux Vulkan smoke rendering **3 frames** with **0 Vulkan validation errors**;
- a recorded full Python suite with **7,520 passed, 4 skipped, 0 failed**;
- retail `SHIFT.exe` entry-point execution against the real PC 1.02 image;
- explicit fail-closed evidence for the current retail startup blocker.

Relevant evidence:

- [`evidence/pcode_full_lowering_linux_build_20261018.json`](evidence/pcode_full_lowering_linux_build_20261018.json)
- [`evidence/pcode_full_lowering_delta_20261018.json`](evidence/pcode_full_lowering_delta_20261018.json)
- [`evidence/recompiled_pcode_pe32_vulkan_runtime_20261018.json`](evidence/recompiled_pcode_pe32_vulkan_runtime_20261018.json)
- [`evidence/recompiled_pcode_kernel32_crt_startup_20261018.json`](evidence/recompiled_pcode_kernel32_crt_startup_20261018.json)
- [`evidence/recompiled_pcode_pe32_guest_thread_state_20261018.json`](evidence/recompiled_pcode_pe32_guest_thread_state_20261018.json)
- [`evidence/recompiled_pcode_pe32_fiber_memory_frontier_20261018.json`](evidence/recompiled_pcode_pe32_fiber_memory_frontier_20261018.json)

## Build and test

### Python tooling

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

Dependencies include a C++ toolchain, CMake, Vulkan development files, XCB and `glslangValidator`.

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

## Running the recompiled guest bridge

The full generated P-code ELF is not committed to Git. After producing or restoring the artifact described by the evidence records, the runtime can load it together with a PE32 image:

```bash
native_runtime/build/shift_runtime \
  --scene-set out/native-scene-vulkan \
  --shader-dir native_runtime/build/shaders \
  --recompiled-module /path/to/libnfs_shift_pcode_partial.so \
  --pe-image /path/to/SHIFT.exe \
  --recompiled-entrypoint
```

A selected lowered function can also be executed at each native fixed step with `--recompiled-step ADDRESS`.

See [`native_runtime/README.md`](native_runtime/README.md) for the current runtime options and exact limits.

## Evidence policy

This project intentionally separates **what executes** from **what has been proven equivalent**.

- PC retail 1.02 is the primary semantic authority.
- P-code coverage is not behavioral parity.
- Successful linking is not successful game startup.
- Successful startup progress is not a playable build.
- Static executable evidence, runtime observations and resource identity remain separate until explicitly joined.
- Xbox 360 material may be used for navigation/corroboration, not as a replacement for PC proof.
- Callgraph proximity is not ownership.
- Equal numeric values are not provenance.
- Visual similarity is not resource identity.
- Host pacing cannot substitute for recovered retail scheduler evidence.
- Fixtures and synthetic scenes validate infrastructure, not retail gameplay.
- Unsupported behavior should fail closed instead of being guessed.

Research-input identities and hashes are centralized in [`coordination/research_inputs.lock.json`](coordination/research_inputs.lock.json).

## Repository map

| Path | Purpose |
| --- | --- |
| `native_runtime/` | Linux runtime, guest execution bridge, physics/runtime reconstruction, XCB/Vulkan integration |
| `native_vulkan/` | Native Vulkan utilities and rendering support |
| `tools/ghidra/` | Static-analysis exports, corpus generation, lowering and evidence tooling |
| `evidence/` | Machine-readable proof, coverage and runtime records |
| `coordination/` | Native playable-slice execution state and development ownership |
| `docs/` | Technical notes for recovered systems and recompilation/runtime frontiers |
| `tests/` | Python regression and evidence checks |
| `native_capture/` | Bounded runtime-capture infrastructure |
| `src/graphics/d3d9/` | D3D9-oriented reconstruction/capture work |
| `shift_importer.py` | Retail resource-import pipeline entry point |

## Project goal

The target is not merely to produce compilable code. The target is a native Android/ARM64 game that runs original retail resources and recovered game logic through a documented, testable and evidence-backed runtime. Linux/Vulkan is the reference environment for advancing and validating the shared runtime.

The nearest whole-program milestone is:

```text
real SHIFT.exe
+
complete required guest startup/runtime services
+
full lowered game-code dispatch
+
retail resource initialization
+
native graphics/runtime integration
=
first real in-game execution on Linux, then the same portable path on Android/ARM64
```

The first in-game execution on Linux is an intermediate validation milestone. The final milestone is playable Android/ARM64 gameplay grounded in the PC retail executable and original game resources.
