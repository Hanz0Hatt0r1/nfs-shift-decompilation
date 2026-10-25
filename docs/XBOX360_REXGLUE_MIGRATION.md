# Xbox 360 + ReXGlue migration plan

## Decision and scope

On 2026-10-22 the project selected the Xbox 360 retail version of Need for Speed: SHIFT as the **primary proposed** source for a native Linux / Android ARM64 port. ReXGlue SDK is the first-choice AOT compiler/runtime foundation. The older PC 1.02 P-code recompilation is preserved and moved to a research/maintenance role.

This remains a **pre-playability migration**, not a successful port. The exact retail XEX, individual splash readbacks, and bounded Linux guest/GPU runs are recorded in the gate ledger. The main menu and an offline race are still unverified.

## Linux AMD64 runtime frontier (2026-10-25)

A matched Linux AMD64 launch reproduced `SIGBUS` in `Memory::Initialize` while `/dev/shm` held 14 unreferenced `xenia_memory_*` objects from interrupted runs. Unlinking only those stale names allowed the same host executable, ReXGlue runtime, GPU plugin, and retail XEX to pass guest-memory initialization and continue through repeated retail submit/CopyConvert activity for a bounded 22-second run. It did not establish menu or race progress.

The old runtime left one more named 4.6 GB shared-memory object after the bounded run was stopped. SDK commit `58e4d4b973aac482a1fb08a665195a30c7b5e5b9` adds unlink-after-open for private POSIX guest memory mappings. Its Release runtime loaded through a temporary `LD_LIBRARY_PATH` override with the unchanged P1 executable and selected plugin. A bounded 25-second exact-XEX run passed guest-memory initialization and continued into captured draw submissions and Copy/Convert activity; `/proc/<pid>/maps` showed this run's mapping as `(deleted)` while it was alive. The two focused POSIX mapping tests pass on the identical patch. A separate live P2 runtime owned the other named mapping observed during the run and was left untouched. This does not establish visible output, the main menu, or a race, and the SDK fix is not yet in the app's default runtime. See [the shared-memory pressure evidence](../evidence/xbox360_linux_shm_backing_pressure_20261025.json) and [the unlink integration evidence](../evidence/xbox360_linux_shm_unlink_integration_20261025.json).

A follow-up 45-second read-only GDB trace with that runtime observed source-0 and source-1 interrupt callbacks, advancing software-ring cursors, and guest wait returns. The separate deferred-record queue remained `0/0`; its producer and registered callback were not hit. This supports progress through the sampled retail wait path but does not identify why the callback stays absent or prove menu/race progress. The trace also confirmed that the local extracted `default.pe` is not byte-equivalent to the live-memory-derived exact-XEX ELF at `0x823A4758`; use the exact live ELF record for static claims at that address. See [the patched-runtime queue trace](../evidence/xbox360_linux_guest_queue_trace_patched_runtime_20261025.json).

The exact live-memory-derived PPC ELF also narrows the `cameraconfig.xml` miss: the retail file reader maps the failed open to sentinel `-5`, the config probe returns `false`, and its outer initializer cleans up two associated objects before continuing into later initialization. This caller path does not justify changing VFS status semantics or establish a main menu/race. See [the missing-asset caller evidence](../evidence/xbox360_linux_missing_asset_caller_semantics_20261025.json).

A 90-second exact-XEX trace also followed both loose `menu_background.xml` misses through the retail resource loader. The parent stores the child loader result at offset `1456`, sets its own return value to `1`, and returns on the observed path, so the miss does not directly fail that parent initializer. The last 14-packet draw submission precedes the first miss by about 0.75 seconds; no later draw submission appears before the run ends. That timing makes this a useful transition to trace, but does not establish causality or that the XML is irrelevant to later visuals. No VFS alias is justified. See [the menu-background return-flow evidence](../evidence/xbox360_linux_menu_background_missing_flow_20261025.json).

A separate input trace followed the retail `XamInputGetKeystrokeEx` poll at `0x823077D4`, which requests device flag `2`. The SDK previously rejected that query before consulting input drivers, and the MNK event queue was never populated. The SDK fix accepts keyboard-selected queries, filters SDL gamepad events by device type, and forwards MNK raw keydown/up/repeat events. In a bounded exact-XEX run with `--mnk_mode=true`, Enter and Space keydown/up records returned success through the retail import. This verifies delivery to the guest poll, not frontend consumption, main-menu entry, or race progress. The distinct gamepad `GetState` path remains under investigation. See [the retail keyboard keystroke trace](../evidence/xbox360_linux_keyboard_keystroke_route_20261025.json) and [SDK PR #5](https://github.com/Hanz0Hatt0r1/rexglue-sdk/pull/5), stacked on [SDK PR #4](https://github.com/Hanz0Hatt0r1/rexglue-sdk/pull/4).

## Proposed pipeline

```text
external, lawful Xbox 360 retail extraction
    -> original default.xex + version/hash lock
    -> XEX metadata, imports, PPC function/disassembly inventory
    -> pinned ReXGlue SDK PPC -> portable C++
    -> ReXGlue Xbox 360 kernel/runtime + SHIFT-specific integrations
    -> original game Xenos commands -> Vulkan backend
    -> Linux x86-64 validation
    -> Linux ARM64 validation
    -> Android ARM64 (window/input/audio/files/lifecycle)
```

Do not assume that the PC `SHIFT.exe` shares addresses, call conventions, resource variants, shader binaries or gameplay behavior with the Xbox executable. Match concepts only from observed cross-version evidence.

## Why ReXGlue, and what it does not guarantee

ReXGlue is an upstream, early-development PPC AOT project with Xbox 360 runtime infrastructure and an Xenos/Vulkan graphics backend. The local Linux AMD64 package is linked to the official v0.10.0 source commit `f5337cdc947ff6d4c4196737e2c807a48f2a1fc2`; this diagnostic pin is recorded in the ledger but is not yet a checked-in build integration. The SDK includes Linux x86-64/ARM64 build targets and Android-related platform interfaces; this is **not** proof that an NFS SHIFT Android executable builds, launches, renders or plays. Future SDK changes must be separately versioned and audited.

References:
- https://github.com/rexglue/rexglue-sdk
- https://github.com/xenia-project/xenia
- https://github.com/arcanite24/pinyon-shift (precedent for a *different* Xbox 360 racing game, not SHIFT compatibility evidence)

## Implementation boundaries

| Boundary | Upstream starting point | SHIFT-specific verification needed |
| --- | --- | --- |
| PPC AOT | ReXGlue compiler/codegen | XEX coverage, indirect control flow, PPC floating/vector semantics, generated-code parity |
| Xbox OS/HLE | SDK runtime / Xenia-derived services | Imports, title storage, file formats, scheduling, threading, timing, exceptions |
| GPU | Xenos command processor and Vulkan path | Title's actual shaders, texture layouts, EDRAM/render target behavior, depth/blend, presentation |
| Assets | Existing PC importers may help conceptually | Xbox archive variants, compression, endianness, shader/resource identity |
| Hosts | Linux SDK platform layer | x86-64 initial test, ARM64 separate executable proof, Android lifecycle and input/audio |
| Vulkan | ReXGlue Vulkan backend | **Vulkan 1.1 minimum**; feature/extension audit and actual runtime check |

### Vulkan 1.1 compatibility is a release gate

The SDK can reference features introduced after 1.1 or available only as extensions. Do not assume the shader translator and GPU backend will run on a 1.1-only device merely because the project builds with Vulkan headers. Record the precise device extensions/features, their promotion level and fallback strategy. If a 1.2/1.3 dependency cannot reasonably be removed, document the cost and request an explicit project-level decision before changing the minimum.

### Migration without throwing away PC work

Preserve:
- `native_runtime/`, `native_vulkan/`, current graphics and capture code, `tools/`, `tests/`, `src/`, `evidence/`, and resource importers;
- hash/identity research, original PC draw captures and fixture regressions;
- existing PRs and generated historical playable-slice status.

No new Xbox runtime should depend on the PC Win32 shim by default. Reuse neutral library pieces (compression, geometry/data conversion, test harnesses) only after a format, ABI or behavior check. PC parity observations are reference data, not Xbox correctness proofs.

## Immediate engineering gates and artifacts

**X0 input intake:** keep an external extracted Xbox game directory, record SHA-256 for XEX and tested asset samples plus XEX build/region/title identification. Add reproducible manifest/evidence metadata only. If there is no verified `default.xex`, stop before claiming real SDK conversion.

**X1 compiler preflight:** freeze a ReXGlue commit, run its real XEX analysis/codegen path, record accepted/rejected functions or instructions, generated artifacts, unresolved PPC semantics and API/import inventory. Do not make up config layouts or addresses before inspecting the XEX.

**X2 Linux first boot:** produce a Linux x86-64 executable using that frozen version, record actual entrypoint execution and trace boundary, no synthetic substitutes or skipped exceptions.

**X3 renderer:** first *real Xbox SHIFT* GPU command and deterministic output; Vulkan validation and capability report; one synthetic SDK frame alone is not success.

**X4 gameplay:** actual frontend → controllable offline race; record input, audio, resource loading and sustained runtime outcomes.

**X5 host portability:** recompiled Linux ARM64 runtime tests followed by Android ARM64 separately, including input/storage/audio/lifecycle.

**X6 Vulkan 1.1:** successful required scene/draw coverage on a Vulkan 1.1-capable device using only supported capabilities, or an explicit evidence-backed blocker and design decision.

## Versioning, CI, review and fallback

- Track the current gate results in `coordination/xbox360_rexglue_status.json`; validator rejects unsubstantiated verified states.
- Keep the scaffold check independent of proprietary inputs. Real XEX integration CI may use local/private runners without publishing copyrighted artifacts.
- Avoid mass-closing PC PRs or moving source trees until the new Xbox compiler/bootstrap gates are independently demonstrated.
- At X1, X2 and X6, reconsider feasibility against the existing PC path if unresolved blockers dominate the budget.
- The archived original PC roadmap and README live in `docs/PC_RECOMPILATION_ROADMAP_20261022.md` and `docs/PC_RECOMPILATION_README_20261022.md`.
