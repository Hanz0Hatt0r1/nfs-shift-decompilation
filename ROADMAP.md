# Need for Speed: SHIFT — Full Native Linux Runtime Roadmap

This roadmap defines the path to the **full execution of the original PC retail 1.02 game on Linux** using the recovered/lowered game code, the original retail resources, and the native Linux runtime.

The previous Silverstone/BMW vertical-slice milestone is no longer a project target. Its documents and evidence remain useful historical research, but they **must not drive task selection or readiness claims**.

The project goal is now:

```text
original PC retail SHIFT.exe
+
complete lowered game-code execution
+
sufficient Win32 / runtime compatibility
+
original retail initialization
+
original resource loading
+
original game-system execution
+
native Linux graphics / audio / input integration
+
menu -> race -> continuous gameplay
=
full native Linux execution of Need for Speed: SHIFT
```

## Current position — 2026-10-18

The project has already crossed the basic code-generation boundary:

| Area | Current state |
| --- | --- |
| Frozen PC function corpus | **41,538 functions identified** |
| P-code lowering | **41,538 / 41,538 lowerable** |
| Machine instructions covered | **2,088,152 / 2,088,152** |
| P-code operations covered | **9,600,713** |
| Linux lowered module | **Full corpus links as native ELF exports** |
| Original PE32 image loading | **Implemented** |
| Original PE32 entry point | **Executable through guest runtime** |
| Import/IAT dispatch | **Implemented with fail-closed API boundary** |
| Guest threads | **Cooperative multi-thread scheduling implemented** |
| Guest host parallelism | **Not implemented / not currently required** |
| Instruction-level preemption | **Not implemented** |
| Vulkan runtime shell | **Operational** |
| Retail entry-point completion | **Not yet proven** |
| Game initialization completion | **Not yet proven** |
| Menu | **Not reached** |
| Race | **Not reached** |
| Full gameplay | **Not reached** |

The newest scheduler work changed the immediate frontier. The previous retail probe stalled inside a guest worker because workers were executed synchronously. A cooperative guest scheduler now exists, but the **real retail entry point has not yet been rerun with the complete 41,538-export P-code ELF**.

Therefore the current highest-priority task is:

> **Restore or rebuild the complete lowered P-code ELF and rerun the real retail `SHIFT.exe` entry point through the cooperative scheduler until the first new fail-closed blocker is reached.**

Evidence for the current frontier:

- [`docs/PROCESS_0_PCODE_NATIVE_LOWERING.md`](docs/PROCESS_0_PCODE_NATIVE_LOWERING.md)
- [`docs/RECOMPILED_PCODE_VULKAN_PE32_LOADER.md`](docs/RECOMPILED_PCODE_VULKAN_PE32_LOADER.md)
- [`evidence/pcode_native_lowering_coverage_full_20261018.json`](evidence/pcode_native_lowering_coverage_full_20261018.json)
- [`evidence/recompiled_pcode_vulkan_frontier_20261018.json`](evidence/recompiled_pcode_vulkan_frontier_20261018.json)
- [`evidence/recompiled_pcode_guest_cooperative_scheduler_20261018.json`](evidence/recompiled_pcode_guest_cooperative_scheduler_20261018.json)

---

## Stage 0 — Reproducible complete lowered runtime artifact

### Objective

Make the complete lowered retail-code artifact reproducibly available to the runtime and CI/probe environment.

### Required work

- Rebuild or restore the full Linux ELF containing all **41,538** lowered exports.
- Pin the exact corpus, lowering tool revision, generated source hashes, compiler inputs and linked ELF hash.
- Make restoration/build instructions deterministic enough that a clean machine can reproduce or fetch the same artifact.
- Keep multi-gigabyte generated artifacts outside Git while keeping manifests and hashes in Git.
- Ensure frontier override/supplement modules can be loaded on top of the full base module without ambiguous duplicate resolution.

### Exit criteria

- The runtime can load the complete base ELF.
- Export count and hashes match recorded evidence.
- The retail PE32 image and complete lowered module can be launched together from a documented command.
- The current retail startup probe is runnable without manually reconstructed local state.

This stage is an infrastructure gate and should be completed before interpreting further startup failures.

---

## Stage 1 — Complete the retail PE32 entry point

### Objective

Run the original retail `SHIFT.exe` entry point to completion under the Linux guest runtime.

### Current method

Use a strict blocker loop:

```text
run retail entry point
        |
        v
first unsupported state / API / function / synchronization condition
        |
        v
recover exact requirement
        |
        v
implement minimum source-backed behavior
        |
        v
add regression + evidence
        |
        v
rerun from the retail entry point
```

Do not implement speculative Windows APIs in bulk.

### Expected blocker classes

#### Missing P-code exports

When execution reaches a function not present in the frozen lowered export set:

- recover its exact instructions/P-code;
- determine why it is outside the frozen corpus;
- add a bounded supplemental/frontier export;
- record provenance and source hashes;
- prefer fixing the generic corpus/lowering pipeline when the missing export reveals a general extraction problem.

#### Win32 imports

Implement only imports actually reached by retail execution.

Likely remaining families include:

- additional thread/process APIs;
- event and synchronization semantics;
- file-system behavior;
- memory mapping/protection;
- locale and CRT-adjacent helpers;
- exception-related APIs;
- window/input APIs;
- DirectX-facing imports.

Each implementation must preserve the x86 ABI and fail closed outside its proven scope.

#### Thread scheduling and synchronization

The runtime now has cooperative guest threads. Extend it only as demanded by retail behavior:

- event waits integrated with the scheduler;
- cross-thread mutex/critical-section ownership;
- alertable waits/APC behavior if reached;
- fiber creation/switching if reached;
- timeout semantics;
- thread creation/exit/join lifecycle;
- TLS/TEB state correctness across scheduling;
- scheduler fairness and deadlock diagnostics.

Instruction-level preemption or host-thread parallelism should be added only if retail evidence proves cooperative scheduling is insufficient.

#### Exceptions

Current exception support is intentionally narrow.

If retail startup requires actual SEH:

- recover the exact exception path;
- model x86 exception records/context;
- implement required registration/unwind behavior;
- connect `SetUnhandledExceptionFilter` only when proven necessary;
- keep unsupported exception forms fail closed.

### Exit criteria

Stage 1 is complete when:

- the original PE32 entry point returns/completes normally;
- no startup worker remains permanently blocked due to missing runtime semantics;
- no unsupported import/function is encountered during that entry-point execution;
- completion is reproducible in tests/evidence.

This is the first major whole-program milestone.

---

## Stage 2 — Complete Windows/runtime compatibility required by game initialization

### Objective

Continue execution after the PE entry point until the game's persistent core systems are initialized.

Entry-point completion does **not** imply that the game is initialized.

### Required work

Track runtime behavior after startup and close only the compatibility surfaces the game actually consumes.

Priority areas:

- process and module state;
- thread scheduling and synchronization;
- heap/virtual-memory behavior;
- file I/O and directory enumeration;
- registry/configuration behavior if reached;
- timing/performance counters;
- input-device initialization;
- window creation/message processing;
- DirectInput/XInput compatibility as required;
- DirectSound/audio initialization as required;
- D3D9 initialization surface;
- remaining CRT/platform glue;
- persistent guest handles and object lifetime.

### Compatibility policy

The Linux runtime is **not intended to become a general Wine implementation**.

Only implement the Windows semantics required by this retail executable, but implement those semantics correctly enough for the game to behave as expected.

### Exit criteria

- Core game managers initialize.
- Main game loop is entered.
- Retail resource/bootstrap code begins operating through original control flow.
- No test-only substitute is needed to force the game into its main loop.

---

## Stage 3 — Original retail resource initialization

### Objective

Allow the original game logic to discover, open, decode and instantiate the retail data it expects.

The repository already has a substantial independent BFF/resource reconstruction pipeline. That work becomes supporting evidence and tooling; the primary target is now to make **original game code consume the retail resources during real startup**.

### Required work

- Reproduce the file-system view expected by the game.
- Verify BFF/package discovery through original code.
- Support required file handles, seeks, mapping and async behavior.
- Recover path/config/environment assumptions.
- Validate package/resource hashes against known retail inputs.
- Diagnose any original decompression/resource parser failures inside the guest.
- Reuse existing neutral resource tooling to inspect and verify what the retail code is trying to load.

### Exit criteria

- Original resource initialization runs through the retail code path.
- Required packages are discovered and opened.
- Resource managers reach a stable initialized state.
- Failures can be correlated to exact retail assets rather than synthetic replacements.

---

## Stage 4 — Main loop, jobs, timing and stable multi-thread execution

### Objective

Run the real game loop continuously without deadlock, uncontrolled spin, or semantic scheduler substitutions.

### Required work

- Identify the actual main-loop boundary.
- Recover scheduler/job-worker topology from runtime evidence.
- Make cooperative guest scheduling support all synchronization primitives actually used.
- Reproduce required timing relationships without equating host frame timing to retail game timing.
- Track worker liveness, waits, wakes and ownership.
- Add diagnostics for:
  - runnable threads;
  - blocked threads;
  - wait objects;
  - guest PCs/call stacks;
  - scheduler transitions;
  - deadlocks and starvation.

### Exit criteria

- The game loop remains alive for an extended bounded run.
- Guest workers make forward progress.
- No known busy-loop is caused by missing scheduling semantics.
- Timing-sensitive subsystems initialize consistently across repeated runs.

---

## Stage 5 — Original rendering path to Linux Vulkan

### Objective

Make rendering produced by the original game logic visible through the Linux runtime.

The existing native Vulkan scene renderer is useful infrastructure, but the target is no longer a manually assembled Silverstone/BMW scene. The target is **render commands/state driven by the original retail game execution**.

### Required work

Determine the shortest correct path from the game's original graphics behavior to Vulkan.

Likely workstreams:

#### D3D9-facing compatibility

- device creation;
- swap chain/presentation;
- render targets/depth surfaces;
- vertex/index buffers;
- textures;
- declarations/FVF;
- shaders;
- render states;
- sampler/texture-stage state;
- constants;
- draw calls;
- resource lifetime/reset behavior.

#### Translation/adaptation

Map the D3D9 semantics actually used by SHIFT to Vulkan equivalents.

Do not attempt to implement the entire D3D9 API if unused.

#### Shader path

- recover/consume retail shaders;
- translate or recompile them where necessary;
- preserve constant/register semantics;
- validate render-state interaction.

#### Presentation

- connect the game's frame boundary to the native XCB/Vulkan presentation loop;
- handle resize/reset semantics required by the retail code;
- ensure guest rendering does not depend on test-only scene submission.

### Exit criteria

- Original game code creates the graphics device successfully.
- Original game draw calls reach Vulkan.
- The first retail-generated visible frame is presented.
- Synthetic MGEO/triangle rendering is no longer required as proof of game rendering.

This is the second major whole-program milestone.

---

## Stage 6 — Reach and operate the frontend/menu

### Objective

Reach a stable, interactive retail frontend.

### Required work

- complete UI resource loading;
- input routing;
- text/font rendering;
- frontend state machines;
- profile/save handling needed for offline operation;
- audio initialization needed by frontend flow;
- video/Bink behavior: implement, substitute safely, or explicitly skip only where the game tolerates it;
- configuration persistence;
- controller/keyboard mapping.

Online services, EA account infrastructure and matchmaking are not required for the offline native target unless startup hard-depends on a local stub contract.

### Exit criteria

- Boot reaches the retail menu/front-end.
- Keyboard/controller input changes menu state.
- Menu rendering is produced by original game execution.
- The user can navigate to an offline race setup without debug state injection.

This is the first user-visible usability milestone.

---

## Stage 7 — Load and start a real offline race

### Objective

Transition through the original game flow from frontend into a real race using retail resources.

### Required work

- track selection;
- vehicle selection;
- profile/session state;
- world/track streaming;
- vehicle asset initialization;
- physics initialization;
- camera initialization;
- opponent/AI initialization as applicable;
- HUD;
- audio;
- race-state transition;
- resource lifetime across frontend -> gameplay.

Existing Silverstone/BMW reverse-engineering evidence is useful here for diagnosis, but **must not replace the original retail initialization path**.

### Exit criteria

- An offline race loads through the retail frontend/state machine.
- Track and vehicle are instantiated by original game code.
- The race begins without synthetic state injection.
- Camera, physics, input and rendering all advance continuously.

This is the first **playable original-game milestone**.

---

## Stage 8 — Gameplay completeness

### Objective

Move from “a race starts” to a practically playable offline game.

### Required work

Validate and repair:

- steering/throttle/brake/clutch;
- drivetrain and wheel behavior;
- collision/contact;
- suspension;
- timing and race rules;
- AI/opponents;
- camera modes;
- HUD;
- pause/restart;
- damage;
- audio;
- input devices;
- track loading/streaming;
- vehicle variants;
- frontend <-> race transitions;
- save/profile persistence;
- repeated race loading without state leaks.

### Exit criteria

- Multiple tracks and vehicles can be selected and driven.
- Race restart and return-to-menu work.
- No critical subsystem depends on synthetic/test-only state.
- Extended gameplay runs without deterministic deadlock/crash.

---

## Stage 9 — Behavioral parity and hardening

### Objective

Turn a functioning port into an evidence-backed reconstruction with known compatibility boundaries.

### Required work

- compare important runtime state with PC retail captures;
- validate timing-sensitive systems;
- validate physics outputs;
- validate rendering state and frame behavior;
- validate resource identities;
- validate input and camera behavior;
- remove temporary overrides whose generic source problem has been fixed;
- reduce special-case API behavior where general retail behavior is understood;
- improve diagnostics without changing semantics;
- document unsupported online/media/platform features;
- improve clean-machine reproducibility.

### Exit criteria

- Known differences from PC retail are explicit and bounded.
- Core offline gameplay behavior is reproducible.
- Runtime failures produce actionable guest-state diagnostics.
- Build/artifact restoration is documented and repeatable.
- CI covers the stable startup, menu and gameplay smoke paths.

---

## Work-selection rule

The mandatory question before substantial work is now:

> **Какой конкретный blocker полноценного запуска оригинального SHIFT.exe снимает эта работа?**

A task should normally be deferred if it does not advance one of these edges:

```text
retail entry point
    ->
game initialization
    ->
main loop
    ->
retail resources
    ->
original rendering
    ->
frontend
    ->
offline race
    ->
continuous gameplay
    ->
parity / hardening
```

Do not prioritize work merely because a subsystem is interesting or historically belonged to the vertical slice.

---

## Blocker-handling protocol

Every runtime frontier should use the same process:

1. run the freshest retail probe;
2. stop at the first deterministic blocker;
3. capture exact guest function, call stack, API/state and relevant inputs;
4. determine whether the blocker is:
   - missing code,
   - lowering defect,
   - Win32 compatibility,
   - scheduler/synchronization,
   - exception behavior,
   - resource/file-system,
   - graphics,
   - audio/input,
   - game-state logic;
5. implement the minimum evidence-backed correction;
6. add regression coverage;
7. record machine-readable evidence;
8. rerun from the original retail startup path.

A later blocker is not actionable until earlier execution reaches it naturally.

---

## Readiness metrics

Do **not** use historical phase numbers or vertical-slice provider counts as project readiness metrics.

Track whole-program execution milestones instead:

| Metric | Meaning |
| --- | --- |
| Full P-code export coverage | Can all recovered frozen functions execute as lowered host code? |
| Retail entry point complete | Does original startup complete? |
| Main loop reached | Is persistent original game execution active? |
| Guest threads live | Do required workers schedule and synchronize correctly? |
| Retail resources initialized | Does original code initialize retail assets/packages? |
| D3D9 device initialized | Has original graphics startup completed? |
| First retail frame presented | Has original rendering reached Vulkan/presentation? |
| Frontend interactive | Can the retail menu be operated? |
| Offline race started | Has original game flow entered a real race? |
| Continuous gameplay | Can the race run interactively and stably? |
| Multi-track/vehicle coverage | Does gameplay generalize beyond one selected case? |
| Retail parity | Are important differences understood and bounded? |

These should eventually be represented by machine-readable evidence and generated status, rather than hand-maintained prose.

---

## CI strategy

CI should follow stable capability families rather than historical phase numbers.

Primary gates should evolve toward:

```text
lowering / corpus
PE32 loader
guest ABI + Win32 imports
guest scheduler
retail startup probe
resource initialization
graphics translation
Vulkan validation
frontend smoke
offline race smoke
extended gameplay smoke
```

Rules:

- add focused pytest/CTest tests for every fixed blocker;
- retain fail-closed negative tests;
- preserve a small synthetic fixture path for deterministic infrastructure testing;
- separately maintain retail-input probes where licensed local inputs are required;
- do not treat fixture success as retail startup success;
- do not weaken Vulkan validation or evidence checks to make the probe advance.

---

## Evidence policy

The project continues to use PC retail 1.02 as the primary semantic authority.

- Successful lowering is not behavioral parity.
- Successful linking is not game startup.
- Entry-point completion is not game initialization.
- A rendered synthetic frame is not a retail-rendered frame.
- Reaching the menu is not gameplay completeness.
- Starting one race is not full-game parity.
- Host behavior must not silently replace unknown guest semantics.
- Unsupported behavior should fail closed and identify the next blocker.
- Exact negative evidence is useful when it permanently removes a false hypothesis.

Xbox 360 and other builds may be used for navigation/corroboration, but not to override PC retail evidence.

Research-input identities and hashes remain centralized in:

- [`coordination/research_inputs.lock.json`](coordination/research_inputs.lock.json)

---

## Historical vertical-slice material

The old native playable-slice track is **retired as an active project milestone**.

Files such as:

- `coordination/PLAYABLE_SLICE_STATUS.md`
- `evidence/playable_slice_three_process_execution.json`
- P1/P2/P3 coordination contracts;
- Silverstone/BMW vertical-slice phase documents;

remain in the repository because they contain useful reverse-engineering evidence and recovered subsystem knowledge.

They are historical/supporting inputs only. They must not be used to decide current work, declare current readiness, or block the whole-program runtime path unless the retail execution path independently reaches the same unresolved semantic surface.

---

## Immediate queue

The immediate whole-program queue, in order, is:

1. **Restore/rebuild the complete 41,538-export Linux P-code ELF.**
2. **Rerun real PC retail 1.02 `SHIFT.exe` with the cooperative guest scheduler from current `main`.**
3. **Capture the first new deterministic blocker after the scheduler change.**
4. **Fix that blocker with the minimum evidence-backed implementation and regression.**
5. **Repeat until the PE32 entry point completes.**
6. **Continue the same blocker-driven process until the real game main loop and resource initialization are reached.**
7. **Begin D3D9-to-Vulkan game-rendering integration only when original execution reaches the graphics initialization surface naturally.**

Until step 2 is completed, speculative subsystem expansion is lower priority than obtaining the new retail execution frontier.

---

## Definition of success

The project is considered functionally complete when:

```text
original SHIFT.exe starts
-> original initialization completes
-> original frontend is interactive
-> an offline race loads through retail game flow
-> original vehicle/input/physics/camera/gameplay logic runs continuously
-> original rendering is presented through Linux Vulkan
-> repeated races and frontend transitions remain stable
```

Behavioral hardening and parity work continue after that point until important differences from PC retail are understood, tested and documented.
