# Need for Speed: SHIFT — Android Port Roadmap

This roadmap defines the path to a **native Android/ARM64 port of the original PC retail 1.02 game**.

Linux/Vulkan is the project's **bring-up, debugging and validation platform**, not the final product target. The runtime, recovered game code, graphics backend and platform abstractions must therefore be designed so that successful Linux bring-up transfers to Android instead of creating a Linux-only implementation.

The retired Silverstone/BMW vertical slice is not an active milestone. Its code, captures and evidence remain useful research material only.

## Final target

```text
original PC retail SHIFT.exe / recovered x86 game code
+
complete portable lowered-code execution
+
SHIFT-required Win32 compatibility
+
original retail initialization and game systems
+
SHIFT-specific D3D9 -> Vulkan backend
+
platform-neutral runtime core
+
ARM64 host support
+
Android Vulkan / input / audio / storage / lifecycle
+
frontend -> offline race -> continuous gameplay
=
native Android port of Need for Speed: SHIFT
```

The intended architecture is:

```text
                 original SHIFT game logic
                           |
                           v
                lowered portable game code
                           |
                           v
          guest x86 state + Win32 compatibility
                           |
          +----------------+----------------+
          |                                 |
          v                                 v
 original renderer logic             other game systems
          |
          v
 SHIFT D3D9-facing compatibility/backend
          |
          v
 portable Vulkan renderer core
          |
     +----+----------------------+
     |                           |
     v                           v
Linux platform layer       Android platform layer
XCB/Wayland + Vulkan       ANativeWindow + Vulkan
dev/debug/validation       shipping target
```

The renderer logic above the D3D9 boundary should remain original wherever possible. The **D3D9 backend itself must be replaced by a native Vulkan implementation of the subset actually used by SHIFT**.

---

## Current position — 2026-10-18

| Area | Current state |
| --- | --- |
| Frozen PC function corpus | **41,538 functions identified** |
| P-code lowering | **41,538 / 41,538 lowerable** |
| Machine instructions covered | **2,088,152 / 2,088,152** |
| P-code operations covered | **9,600,713** |
| Linux lowered module | **Full corpus links as native ELF exports** |
| Original PE32 image loading | **Implemented** |
| Original PE32 execution | **v111 clean Release build reaches 80,626 dispatches / 1,417 unique functions and renders 120 frames with Khronos validation enabled and zero errors** |
| Import/IAT dispatch | **Implemented with fail-closed API boundary** |
| Guest threads | **Cooperative multi-thread scheduling implemented** |
| Vulkan runtime shell | **Operational on Linux** |
| D3D9 capture tooling | **Retail capture audited: 4,309 frames and 1,581 Silverstone target draw hits; no VB/IB payloads or resource path/SHA identity yet** |
| Complete D3D9 -> Vulkan game backend | **Not implemented** |
| Host-architecture-neutral runtime | **Not yet proven** |
| ARM64 lowered-runtime execution | **Generic P-code fixture passes; full corpus/runtime not yet proven** |
| Android platform layer | **Not implemented** |
| Retail entry-point completion | **The entry-point call remains active while the main guest thread runs at `0x006472d0`; v111 crosses the prior missing-export frontier at `0x0050c8a9`** |
| Game main loop | **Static call path points to the repeated update loop; dynamic loop identity and frontend progress remain unproven** |
| Retail frontend | **Not reached** |
| Offline race | **Not reached** |
| Android gameplay | **Not reached** |

The cooperative guest-thread scheduler has been exercised by the real retail entry point together with the complete lowered P-code ELF. Probe v111 rebuilt `shift_runtime` from this updated `main` in a clean Release directory and enabled `VK_LAYER_KHRONOS_validation`. Using **41,539 exports** (the 41,538-function corpus plus the active startup override) and 31 supplements, it crossed the prior missing-export frontier at `0x0050c8a9`, ran 80,626 guest dispatches across 1,417 unique functions, and rendered all 120 requested host Vulkan frames with zero validation errors. At the end, the main guest thread remained runnable at `0x006472d0`; four workers were waiting. Ghidra shows that helper updating app/timer state and its callers feed a repeated event loop, but the capture does not establish dynamic call-stack identity, frontend progress, input, or a retail D3D9 frame. The full lowered module and supplements still come from the external persistent artifact cache. See the [v111 probe record](evidence/retail_frontier_20261018/entrypoint_probe_v111.json), [probe log](evidence/retail_frontier_20261018/shift-probe-v111-validation.log), and [v110 record](evidence/retail_frontier_20261018/entrypoint_probe_v110.json).

The installed PortProton retail run has a separate D3D9 capture at frame range 0–4309 (308,332 ms; 1,718,778 valid JSON objects). It contains 1,581 draws matching the Silverstone-era target shader inventory, including 537 hits for the crowd-generation shader whose SHA-256 is `d7859cca…00d351a`. The audited report also maps that shader to the proxy trigger signature `ps:b83e3c4ec719e80f`. The capture contains draw-local shader/state evidence, but no vertex/index-buffer payloads, texture snapshots, or exact resource path/SHA pairs, so none of those hits can yet be admitted as a retail mesh in Vulkan. The raw 474 MB capture remains in the external PortProton game directory; its SHA-256 and audit commands are recorded in [the capture audit note](docs/SHIFT_D3D9_CAPTURE_AUDIT_20261018.md). The report records 2,912 duplicate-key lines but zero conflicting duplicate values; duplicate keys still remain a capture-format defect.

The earlier v65-v67 allocator evidence remains useful history, but it is not the latest execution state. The current blockers are proving retail control-flow progress beyond the v111 snapshot and connecting actual D3D9 draw resources to the Vulkan backend. The native Vulkan smoke still uses converted synthetic MGEO geometry. No complete frontend, offline race, or playable retail session has been demonstrated.

The generic `revenginstr` binary80 lowering now executes a synthetic P-code
fixture on ARM64 CI (22 passed, one x86-only `FWAIT` test skipped). This covers
the codec and representative operations only; it does not validate the full
SHIFT corpus, guest x87-state mapping, exact wide-host rounding, or retail
startup. See the [cross-host fixture evidence](evidence/pcode_native_lowering_arm64_binary80_20261018.json).

The current immediate execution frontier is:

> **Reproduce the v111 guest-thread state with a dynamic call trace, verify that the `0x006472d0` path advances through the retail update loop, and wire the first fully captured retail D3D9 draw into the Vulkan translator. Use a resource-triggered capture around `ps:b83e3c4ec719e80f` to collect the bound VB/IB payloads and the minimum texture evidence, then validate identity before admitting that draw.**

At the same time, new infrastructure must avoid introducing additional x86-64/Linux-only assumptions.

Primary evidence:

- [`docs/PROCESS_0_PCODE_NATIVE_LOWERING.md`](docs/PROCESS_0_PCODE_NATIVE_LOWERING.md)
- [`docs/RECOMPILED_PCODE_VULKAN_PE32_LOADER.md`](docs/RECOMPILED_PCODE_VULKAN_PE32_LOADER.md)
- [`evidence/pcode_native_lowering_coverage_full_20261018.json`](evidence/pcode_native_lowering_coverage_full_20261018.json)
- [`evidence/recompiled_pcode_vulkan_frontier_20261018.json`](evidence/recompiled_pcode_vulkan_frontier_20261018.json)
- [`evidence/recompiled_pcode_guest_cooperative_scheduler_20261018.json`](evidence/recompiled_pcode_guest_cooperative_scheduler_20261018.json)
- [`evidence/retail_frontier_20261018/entrypoint_probe_v111.json`](evidence/retail_frontier_20261018/entrypoint_probe_v111.json)
- [`docs/SHIFT_D3D9_CAPTURE_AUDIT_20261018.md`](docs/SHIFT_D3D9_CAPTURE_AUDIT_20261018.md)
- [`evidence/shift_d3d9_capture_audit_20261018.json`](evidence/shift_d3d9_capture_audit_20261018.json)
- [`evidence/shift_d3d9_capture_provenance_20261018.json`](evidence/shift_d3d9_capture_provenance_20261018.json)
- [`evidence/shift_silverstone_target_draw_local_summary_20261018.json`](evidence/shift_silverstone_target_draw_local_summary_20261018.json)
- [full draw-local evidence (gzip)](evidence/shift_silverstone_target_draw_local_20261018.json.gz)

---

## Stage 0 — Reproducible complete lowered artifact

### Objective

Make the complete recovered game-code artifact reproducibly buildable/loadable without relying on one developer machine.

### Required work

- Keep the restored full module containing all **41,538** lowered exports and its required startup supplements reproducible from pinned inputs.
- Pin corpus revision, lowerer revision, generated-source hashes, compiler inputs and resulting module hash.
- Keep large generated artifacts outside Git while keeping deterministic manifests and hashes in Git.
- Make base, supplement and override loading deterministic.
- Document a clean-machine path from authoritative research inputs to a runnable retail probe.
- Keep generated lowered code free of host-ISA assumptions unless explicitly isolated behind a portability layer.

### Exit criteria

- Complete export count is verified.
- Retail `SHIFT.exe` and the complete lowered module can be launched from a documented command.
- The startup probe can be reproduced without hidden local artifacts.
- The same generated source corpus is suitable for both x86-64 and ARM64 host compilation.

---

## Stage 1 — Make the execution core host-architecture neutral

### Objective

Ensure that the recovered x86 game is represented as **guest semantics**, not as accidental x86-64 host semantics.

The final Android target is ARM64. Any host-x86 shortcut that leaks into game behavior is technical debt that can invalidate the Android port.

### Required work

Audit and isolate:

- host pointer width assumptions;
- endianness assumptions;
- unaligned memory behavior;
- x86-specific inline assembly/intrinsics;
- host `CPUID`;
- x87/binary80 dependencies;
- host floating-point environment assumptions;
- atomics and memory-order assumptions;
- `ucontext` or other platform-specific coroutine implementation details;
- page size and virtual-memory assumptions;
- executable/shared-library loading assumptions;
- ELF loader/runtime symbol behavior.

Guest x86 behavior must remain explicit in the runtime:

- x86 register state;
- TEB/TLS;
- x87/SSE semantics where required;
- 32-bit guest pointers;
- Win32 ABI;
- guest atomics/synchronization behavior.

### ARM64 policy

ARM64 portability must not be postponed until the Linux game is fully playable.

As soon as the runtime core can be built independently:

- add an ARM64 compile gate;
- run fixture tests on ARM64 Linux hardware or an equivalent validated environment;
- verify the lowered corpus builds for AArch64;
- add architecture-independent regression fixtures for guest memory, calls, floating-point operations and scheduling.

### Exit criteria

- Core runtime builds on x86-64 and ARM64.
- Lowered game code builds on x86-64 and ARM64.
- Fixture behavior is equivalent across both hosts.
- Known host-specific implementations are isolated behind explicit interfaces.
- No new subsystem may depend directly on x86-64 behavior without a portability plan.

---

## Stage 2 — Complete retail startup on Linux/Vulkan

### Objective

Use Linux as the fastest observable environment to drive the real retail executable through startup and into persistent game execution.

Linux is the reference bring-up target because it provides strong native debugging, sanitizers, Vulkan validation and fast iteration. Success here is a **portability gate**, not the final project goal.

### Blocker loop

```text
run real SHIFT.exe
      |
      v
first deterministic blocker
      |
      v
capture guest PC / call stack / state / input
      |
      v
classify blocker
      |
      v
implement minimum evidence-backed behavior
      |
      v
regression + machine-readable evidence
      |
      v
rerun from original startup path
```

### Blocker classes

- missing/recovered P-code function;
- lowering defect;
- Win32 import;
- process/thread state;
- synchronization;
- exception/SEH behavior;
- file-system/resource access;
- timing;
- window/input;
- audio;
- graphics/D3D9;
- game-state logic.

Do not implement speculative Windows APIs in bulk.

### Scheduler work

Extend the cooperative scheduler only when retail execution proves a requirement:

- event waits;
- mutex/critical-section ownership;
- thread waits;
- alertable waits/APC if reached;
- fiber creation/switching if reached;
- timeout behavior;
- TLS/TEB restoration;
- deadlock/starvation diagnostics.

Host parallelism and instruction-level preemption are not goals by themselves. Add them only if retail behavior cannot be represented correctly without them.

### Exit criteria

- Original PE32 entry point completes.
- Required startup workers make forward progress.
- Game initialization continues into the persistent main loop.
- Startup is reproducible from the original retail path.
- No test-only state injection is required.

---

## Stage 3 — Complete SHIFT-required Win32/platform compatibility

### Objective

Implement the Windows behavior actually required by SHIFT while keeping the implementation portable to Linux and Android.

This project is **not** building a general Wine replacement.

### Required compatibility areas

As reached by retail execution:

- process/module state;
- threads/TLS/TEB;
- synchronization;
- heap and virtual memory;
- files/directories;
- configuration/registry equivalents;
- timing/performance counters;
- locale/CRT helpers;
- exceptions;
- window/message-facing behavior;
- input APIs;
- audio APIs;
- Direct3D9-facing interfaces.

### Portability rule

Windows-compatible semantics belong in the shared runtime core. Native host operations belong behind platform interfaces.

For example:

```text
guest CreateFileA
      ->
portable SHIFT file compatibility layer
      ->
Linux filesystem backend
or
Android storage backend
```

The same separation applies to timing, threads, input, audio and graphics presentation.

### Exit criteria

- Core game managers initialize through original code.
- Main loop remains alive.
- Retail resources begin loading through original control flow.
- Platform-specific host code is isolated from guest/Win32 semantics.

---

## Stage 4 — Original retail resources and filesystem model

### Objective

Make original game code consume the real retail assets and packages on both development and Android targets.

### Required work

- reproduce the file-system namespace expected by SHIFT;
- support required open/read/seek/map/enumeration behavior;
- recover configuration and working-directory assumptions;
- validate BFF/package discovery through original code;
- validate known retail resource hashes;
- use existing resource tooling for diagnosis, not as a replacement game loader;
- separate logical game paths from physical host paths.

### Android considerations

Do not bake desktop filesystem paths into game logic.

Provide an Android-compatible storage model for user-provided/licensed retail data, including:

- app-accessible game-data root;
- persistent writable data/config/save root;
- efficient large-asset reads;
- no dependency on arbitrary Windows drive letters;
- no assumption that APK assets behave like seekable desktop files.

### Exit criteria

- Original package/resource managers initialize.
- Retail assets are resolved by original game logic.
- The logical resource layout is identical across Linux and Android even when physical storage differs.

---

## Stage 5 — Replace the D3D9 backend with portable Vulkan

### Objective

Preserve the original SHIFT renderer logic while replacing its low-level D3D9 execution backend with a **native Vulkan backend designed for both desktop Linux and Android Vulkan drivers**.

This is a mandatory core porting stage.

### What stays original

Where practical, retain original game code for:

- visibility/culling;
- render queues;
- materials;
- animation;
- LOD decisions;
- lighting/game render state;
- world/UI submission;
- shader/material selection;
- frame sequencing.

### What must be replaced

Implement the subset of D3D9 semantics actually used by SHIFT:

- Direct3D/device creation;
- adapter/capability queries needed by the game;
- swap chains and presentation;
- device/reset lifecycle;
- render targets;
- depth/stencil surfaces;
- vertex/index buffers;
- dynamic buffers and locking/update behavior;
- textures, mipmaps and formats;
- vertex declarations/FVF;
- vertex shaders;
- pixel shaders;
- shader constants;
- render states;
- sampler states;
- texture-stage state where used;
- viewport/scissor;
- clears;
- draw calls;
- queries/synchronization if used;
- resource lifetime/reference behavior.

### D3D9 capture as specification evidence

Use the existing retail D3D9 capture path to determine what SHIFT actually does:

```text
retail Windows SHIFT
      ->
D3D9 capture
      ->
used API/state/resource/shader corpus
      ->
portable Vulkan backend requirements
```

Do not implement unused D3D9 surface area merely for API completeness.

### Vulkan architecture

The Vulkan renderer core must not depend on XCB or Android directly.

Use a boundary similar to:

```text
SHIFT D3D9 semantics
        |
        v
portable Vulkan renderer
        |
        +----------------------+
        |                      |
        v                      v
Linux Vulkan surface     Android Vulkan surface
```

Platform-independent code should own:

- Vulkan device/resource abstractions;
- buffer/image management;
- descriptor management;
- pipeline/state translation;
- shader handling;
- synchronization strategy;
- render passes/dynamic rendering strategy;
- D3D9 state cache;
- draw translation.

Platform layer should own only what genuinely differs:

- surface creation;
- window/lifecycle events;
- presentation integration;
- platform capabilities and extension selection.

### Shader path

Build a defined retail shader pipeline:

- capture/recover D3D9 shader bytecode;
- translate to SPIR-V or provide equivalent generated Vulkan shaders;
- preserve D3D register/constant semantics;
- map sampler and texture behavior;
- handle precision explicitly;
- test on Android-class Vulkan implementations, not only desktop GPUs.

### Android-first constraints

Do not make desktop-only Vulkan features a requirement unless an Android fallback exists.

Track:

- Vulkan feature/extension requirements;
- texture format support;
- shader precision;
- descriptor limits;
- memory budgets;
- pipeline cache behavior;
- synchronization cost;
- tile-based GPU behavior;
- render-target transitions;
- device-loss/lifecycle recreation.

### Exit criteria

- Original game code successfully creates its graphics-facing device.
- Original SHIFT rendering calls are translated to Vulkan.
- A retail-generated frame is visible on Linux.
- The same renderer core builds for Android.
- No XCB/Linux object is referenced by the portable graphics core.
- Synthetic vertical-slice rendering is no longer required to prove game rendering.

---

## Stage 6 — Full Linux reference bring-up

### Objective

Reach stable original-game execution on Linux using the same portable core intended for Android.

Linux completion is a **reference milestone**, not project completion.

### Required work

- interactive frontend;
- keyboard/gamepad input;
- audio;
- profile/save support required for offline play;
- original frontend rendering;
- frontend -> race transition;
- world streaming;
- physics;
- camera;
- HUD;
- AI/opponents;
- pause/restart;
- repeated race loading.

### Exit criteria

- Original frontend is interactive.
- An offline race can be selected and loaded through original game flow.
- Original renderer feeds the Vulkan backend.
- Gameplay runs continuously.
- Return-to-menu/restart works.
- No Linux-only shortcut is required by game/runtime semantics.

At this point Linux acts as the behavioral reference for Android work.

---

## Stage 7 — ARM64 parity

### Objective

Run the complete portable runtime/game-code stack on an ARM64 host before Android platform complexity is introduced.

Prefer ARM64 Linux for this milestone because it separates **CPU architecture problems** from **Android platform problems**.

### Required work

Validate:

- complete lowered corpus;
- PE32 guest execution;
- scheduler;
- Win32 compatibility core;
- resources;
- floating point;
- atomics;
- Vulkan renderer;
- shaders;
- game main loop.

Replace or emulate host-specific behavior still blocking AArch64, including any remaining:

- CPUID shortcuts;
- x87 host dependencies;
- binary80 assumptions;
- x86-specific atomics;
- ABI assumptions;
- shared-object loader assumptions.

### Exit criteria

- Same retail startup path runs on ARM64.
- Main loop and renderer operate on ARM64.
- Representative Linux ARM64 gameplay matches x86-64 Linux behavior within defined tolerances.
- Cross-architecture regressions are part of CI/test evidence.

This is the mandatory gate before declaring the runtime Android-ready.

---

## Stage 8 — Android platform layer

### Objective

Attach the portable runtime/game/Vulkan core to Android without forking game semantics.

### Required work

Implement Android-native adapters for:

#### Application lifecycle

- process/activity startup;
- pause/resume;
- surface loss/recreation;
- background/foreground transitions;
- suspend-safe runtime state;
- graceful shutdown.

#### Vulkan presentation

- `ANativeWindow` surface;
- swapchain creation/recreation;
- orientation/size changes;
- Android Vulkan capability selection;
- GPU/driver diagnostics.

#### Input

- gamepads/controllers;
- keyboard where present;
- touch input;
- optional touch-to-game-control mapping;
- Android back/navigation behavior where appropriate.

#### Audio

- portable game-facing audio interface;
- Android low-latency output backend;
- focus/interruption handling;
- lifecycle-safe stream recreation.

#### Storage

- retail game-data location;
- saves/profile/config;
- cache;
- scoped-storage-compatible path resolution;
- efficient large-resource access.

#### Timing/threads

- Android-safe clocks;
- thread priorities only where appropriate;
- no dependence on desktop process APIs.

### Exit criteria

- Android app starts the same portable runtime core.
- Retail data is discovered.
- Vulkan device/surface initializes.
- Original game startup executes on ARM64 Android.
- Lifecycle transitions do not corrupt runtime state.

---

## Stage 9 — First playable Android race

### Objective

Reach the first end-to-end playable race on Android through original SHIFT flow.

### Required work

- frontend rendering;
- frontend input;
- track/vehicle selection;
- loading/streaming;
- race initialization;
- physics;
- controls;
- camera;
- HUD;
- audio;
- pause/resume;
- Android lifecycle handling during gameplay.

### Exit criteria

- App launches on supported ARM64 Android hardware.
- Retail frontend is visible and interactive.
- User can start an offline race without debug injection.
- Race renders through Vulkan.
- Vehicle can be controlled.
- Physics/camera/HUD/audio continue advancing.
- Pause/resume survives normal Android lifecycle events.

This is the first **actual Android port milestone**.

---

## Stage 10 — Android performance and device hardening

### Objective

Turn a technically running port into a practical mobile build.

### Required work

Profile and optimize:

- CPU time in lowered game code;
- guest call/dispatch overhead;
- scheduler overhead;
- Vulkan pipeline/state churn;
- descriptor updates;
- shader compilation;
- draw-call overhead;
- asset streaming;
- decompression;
- RAM use;
- Vulkan memory use;
- transient render targets;
- texture residency;
- thermal behavior;
- battery load;
- frame pacing.

### Mobile-specific adaptation

Where required without changing game semantics:

- memory-budget-aware caching;
- configurable resolution;
- render scale;
- texture-quality controls;
- MSAA/AA alternatives;
- shadow/effects quality;
- frame-rate caps;
- shader/pipeline caches;
- touch-control UI;
- controller remapping.

Performance work must not silently replace original gameplay behavior.

### Exit criteria

- Stable gameplay on the defined minimum Android device class.
- Memory use remains within target budgets.
- No sustained thermal/performance failure under representative races.
- Frame pacing is acceptable.
- Multiple tracks and vehicles load repeatedly.
- Save/profile persistence survives app restarts.

---

## Stage 11 — Behavioral parity and release hardening

### Objective

Bound remaining differences from PC retail and make the Android port reproducible.

### Required work

- compare important runtime state against PC retail captures;
- validate physics;
- validate timing;
- validate renderer state;
- validate shaders/materials;
- validate camera/input;
- validate resource identities;
- validate audio behavior;
- remove temporary frontier overrides once generic fixes exist;
- document intentionally unsupported online/platform functionality;
- add deterministic crash diagnostics;
- define supported Android/Vulkan capability floor;
- verify clean Android builds.

### Exit criteria

- Core offline behavior is reproducible.
- Known PC-vs-Android differences are explicit.
- Critical startup/frontend/race smoke paths are automated where possible.
- Runtime failures provide actionable guest state.
- Build instructions and required retail-input hashes are documented.

---

## Parallel workstreams

Not every stage must execute strictly serially.

Three workstreams should proceed in parallel where dependencies allow:

### A — Retail execution frontier

```text
full lowered artifact
-> startup blockers
-> main loop
-> resources
-> frontend/race behavior
```

### B — Graphics backend

```text
D3D9 capture
-> used-state inventory
-> D3D9 compatibility objects
-> shader translation
-> Vulkan draw/state translation
-> retail rendering
```

The graphics backend does **not** need to wait until startup first calls `Direct3DCreate9` before foundational work begins. Retail D3D9 capture already provides useful evidence for designing the backend.

### C — Portability

```text
host-neutral runtime
-> ARM64 compile
-> ARM64 fixtures
-> ARM64 Linux runtime
-> Android platform layer
```

Every new subsystem must be reviewed against the portability workstream.

---

## Work-selection rule

Before substantial work, answer:

> **Какой конкретный blocker Android-порта снимает эта работа?**

Valid answers normally advance at least one of these paths:

```text
retail execution
graphics D3D9 -> Vulkan
host portability / ARM64
Android platform integration
Android gameplay
performance/parity
```

A task that only improves the retired vertical slice, or makes the Linux-only implementation more elaborate without helping Android, should normally be deferred.

---

## Readiness metrics

Historical phase numbers and vertical-slice provider counts are no longer project readiness metrics.

Track:

| Metric | Meaning |
| --- | --- |
| Full P-code coverage | Is the recovered corpus executable by the portable runtime? |
| x86-64 host green | Does the reference runtime work on desktop x86-64? |
| ARM64 host green | Does the same core execute correctly on AArch64? |
| Retail entry point complete | Does original startup complete? |
| Main loop reached | Is persistent original game execution active? |
| Retail resources initialized | Does original code load required retail packages? |
| D3D9 usage inventory | Is the SHIFT-specific graphics surface bounded by captures? |
| Vulkan backend coverage | How much of the used D3D9 surface is translated correctly? |
| First retail Vulkan frame | Has original game rendering reached Vulkan? |
| Linux frontend/race | Is the reference build functionally playable? |
| Android runtime startup | Does the retail path execute on Android ARM64? |
| Android frontend | Is original frontend interactive on-device? |
| Android race | Can an offline race start and run? |
| Device coverage | Which Android/Vulkan capability classes are validated? |
| Performance | Are CPU/GPU/RAM/frame-pacing targets met? |
| Retail parity | Are important deviations known and bounded? |

These should migrate toward generated machine-readable status rather than hand-maintained prose.

---

## CI and validation strategy

Stable capability families should evolve toward:

```text
corpus/lowering
portable runtime
x86-64 fixtures
ARM64 compile
ARM64 fixtures
PE32 loader
Win32 compatibility
guest scheduler
retail startup probe
resource initialization
D3D9 capture contracts
Vulkan backend
shader translation
Linux Vulkan validation
Linux frontend/race smoke
Android build
Android Vulkan startup
Android frontend/race smoke
performance regression
```

Rules:

- every fixed blocker gets a focused regression;
- keep unsupported behavior fail closed;
- preserve deterministic synthetic fixtures for infrastructure;
- do not confuse fixture success with retail success;
- run Vulkan validation on desktop where available;
- test the portable renderer against Android-class feature limits;
- prevent new Linux/x86-64-only dependencies from entering shared core code;
- do not weaken evidence checks merely to advance startup.

---

## Evidence policy

PC retail 1.02 remains the semantic authority for original game behavior.

- 100% lowering is not a working game.
- Linux success is not Android success.
- x86-64 host success is not ARM64 correctness.
- Synthetic Vulkan rendering is not retail rendering.
- A D3D9 API stub is not a correct Vulkan translation.
- A visible menu is not gameplay completeness.
- One working phone is not supported-device coverage.
- Host shortcuts must not silently redefine guest semantics.
- Unsupported behavior should fail closed with enough state to identify the next blocker.

Xbox 360 and other builds may assist navigation/corroboration but do not override PC retail evidence.

Research-input hashes and identities remain centralized in:

- [`coordination/research_inputs.lock.json`](coordination/research_inputs.lock.json)

---

## Historical vertical-slice material

The old native playable-slice effort is retired as an active project milestone.

The following remain only as historical/supporting evidence:

- `coordination/PLAYABLE_SLICE_STATUS.md`;
- `evidence/playable_slice_three_process_execution.json`;
- P1/P2/P3 coordination contracts;
- Silverstone/BMW vertical-slice documents and evidence;
- the standalone scene renderer where it provides reusable Vulkan/resource infrastructure.

They must not determine current priority or readiness.

Reusable implementation may be extracted into the portable renderer/runtime when it fits the Android architecture.

---

## Immediate queue

The complete P-code module has been restored and the cooperative scheduler has been exercised on the retail entry point. The immediate priorities are now:

1. **Trace `Base System` pool descriptor creation and backing-range ownership to explain why the selected list tops out at 129,953,036 bytes for a 254,529,224-byte request; do not force execution past this retail fatal path.**
2. **Keep the compact manifest for the full module, supplements, runtime APIs, retail PE identity, game-data root and probe frontier current; keep generated binaries outside Git.**
3. **Continue the blocker loop through entry-point completion, required startup workers, resource initialization and the persistent main loop.**
4. **Audit the shared runtime for x86-64/Linux-only assumptions and establish an ARM64 compile/test gate.**
5. **Turn existing D3D9 capture data into an explicit inventory of the D3D9 objects, states, formats, shaders and draw paths actually used by SHIFT.**
6. **Refactor Vulkan infrastructure so renderer core and platform surface/window code are cleanly separated.**
7. **Build the SHIFT-specific D3D9 -> Vulkan backend against that captured usage surface.**
8. **Keep Linux as the reference execution/debugging target while continuously checking that shared code remains ARM64/Android-compatible.**
9. **Bring up the same original startup path on Android/ARM64 after the shared execution core and renderer boundaries support it.**

The priority is not “finish Linux and then start Android.” The priority is:

> **Use Linux to solve game/runtime semantics while continuously building the same codebase toward Android/ARM64.**

---

## Definition of success

The project is functionally complete when:

```text
original SHIFT game code
-> runs through the portable recovered-code runtime
-> initializes original retail systems/resources
-> renders through the native Vulkan backend
-> runs correctly on ARM64
-> starts inside an Android application
-> presents the original frontend
-> loads an offline race through original game flow
-> accepts Android/controller input
-> runs physics/camera/HUD/audio continuously
-> survives Android lifecycle transitions
-> provides stable repeated gameplay on supported devices
```

Linux remains the reference/debug build after that point, but **Android/ARM64 gameplay is the project completion target**.
