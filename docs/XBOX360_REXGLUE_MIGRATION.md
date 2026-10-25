# Xbox 360 + ReXGlue migration plan

## Decision and scope

On 2026-10-22 the project selected the Xbox 360 retail version of Need for Speed: SHIFT as the **primary proposed** source for a native Linux / Android ARM64 port. ReXGlue SDK is the first-choice AOT compiler/runtime foundation. The older PC 1.02 P-code recompilation is preserved and moved to a research/maintenance role.

This remains a **pre-playability migration**, not a successful port. The exact retail XEX, individual splash readbacks, and bounded Linux guest/GPU runs are recorded in the gate ledger. The main menu and an offline race are still unverified.

## Linux AMD64 runtime frontier (2026-10-25)

A matched Linux AMD64 launch reproduced `SIGBUS` in `Memory::Initialize` while `/dev/shm` held 14 unreferenced `xenia_memory_*` objects from interrupted runs. Unlinking only those stale names allowed the same host executable, ReXGlue runtime, GPU plugin, and retail XEX to pass guest-memory initialization and continue through repeated retail submit/CopyConvert activity for a bounded 22-second run. It did not establish menu or race progress.

The old runtime left one more named 4.6 GB shared-memory object after the bounded run was stopped. SDK commit `58e4d4b973aac482a1fb08a665195a30c7b5e5b9` adds unlink-after-open for private POSIX guest memory mappings. Its Release runtime loaded through a temporary `LD_LIBRARY_PATH` override with the unchanged P1 executable and selected plugin. A bounded 25-second exact-XEX run passed guest-memory initialization and continued into captured draw submissions and Copy/Convert activity; `/proc/<pid>/maps` showed this run's mapping as `(deleted)` while it was alive. The two focused POSIX mapping tests pass on the identical patch. A separate live P2 runtime owned the other named mapping observed during the run and was left untouched. This does not establish visible output, the main menu, or a race, and the SDK fix is not yet in the app's default runtime. See [the shared-memory pressure evidence](../evidence/xbox360_linux_shm_backing_pressure_20261025.json) and [the unlink integration evidence](../evidence/xbox360_linux_shm_unlink_integration_20261025.json).

A follow-up 45-second read-only GDB trace with that runtime observed source-0 and source-1 interrupt callbacks, advancing software-ring cursors, and guest wait returns. The separate deferred-record queue remained `0/0`; its producer and registered callback were not hit. This supports progress through the sampled retail wait path but does not identify why the callback stays absent or prove menu/race progress. The trace also confirmed that the local extracted `default.pe` is not byte-equivalent to the live-memory-derived exact-XEX ELF at `0x823A4758`; use the exact live ELF record for static claims at that address. See [the patched-runtime queue trace](../evidence/xbox360_linux_guest_queue_trace_patched_runtime_20261025.json).

The exact live-memory-derived PPC ELF also narrows the `cameraconfig.xml` miss: the retail file reader maps the failed open to sentinel `-5`, the config probe returns `false`, and its outer initializer cleans up two associated objects before continuing into later initialization. This caller path does not justify changing VFS status semantics or establish a main menu/race. See [the missing-asset caller evidence](../evidence/xbox360_linux_missing_asset_caller_semantics_20261025.json).

A 90-second exact-XEX trace followed both loose `menu_background.xml` misses through the retail resource loader. The parent stores the child loader result at offset `1456`, sets its own return value to `1`, and returns on the observed path, so the miss does not directly fail that parent initializer. A later 65-second probe observed a zero child result stored at `parent+1456`; a hardware read watchpoint recorded no later access to that field, and candidate reader `0x82B84CD8` was not called with this parent object. This is bounded evidence only: the field could be consumed in a later frontend or race state. Draw submissions stopped around the XML misses, but the traces do not establish causality. No VFS alias is justified. See [the menu-background return-flow evidence](../evidence/xbox360_linux_menu_background_missing_flow_20261025.json).

A separate input trace followed the retail `XamInputGetKeystrokeEx` poll at `0x823077D4`, which requests device flag `2`. The SDK previously rejected that query before consulting input drivers, and the MNK event queue was never populated. The SDK fix accepts keyboard-selected queries, filters SDL gamepad events by device type, and forwards MNK raw keydown/up/repeat events. In a bounded exact-XEX run with `--mnk_mode=true`, Enter and Space keydown/up records returned success through the retail import. A follow-up GDB trace also observed retail `sub_82307790` processing Enter and Space, mapping each event, and reaching the retail keydown/keyup callbacks `0x822FBC48` and `0x822FBCD8`. This verifies consumption by the retail keyboard object, but it does not prove a frontend scene change, main-menu entry, or race progress. The distinct gamepad `GetState` path remains under investigation. See [the retail keyboard keystroke trace](../evidence/xbox360_linux_keyboard_keystroke_route_20261025.json) and [SDK PR #5](https://github.com/Hanz0Hatt0r1/rexglue-sdk/pull/5), stacked on [SDK PR #4](https://github.com/Hanz0Hatt0r1/rexglue-sdk/pull/4).

A retail-consumer trace now follows `sub_82308E60` after its `XamInputGetState` call at guest return address `0x82308EA8`. Successful user-0 polls contain non-neutral button masks `0x0010` and `0x1000`, the retail capability matcher accepts the connected controller, `sub_8230CD00` advances the corresponding per-button edge bytes, and four enabled child-state paths run. These results rule out failure before the retail input edge accumulator as the current frontend blocker; the later frontend action handler and scene transition remain unverified. See [the retail gamepad consumer trace](../evidence/xbox360_linux_retail_gamepad_consumer_20261025.json).

A same-run GDB/uinput trace now correlates six Start/A pulses with 18 successful user-0 retail state samples on the exact Linux build. The candidate raw-mask getter and changed-button dispatcher did not observe those button bits, while the final guest stack sample was inside predicate `0x823A0310`. The trace captures no pixels and cannot identify whether the game was still in an intro scene; frontend consumption and scene transition remain unverified. See [the correlated frontend probe](../evidence/xbox360_linux_gamepad_frontend_consumer_probe_20261025.json).

A 75.62-second follow-up with the current exact-XEX host executable, runtime override, and selected GPU plugin again did not enter retail function `0x82341198`. At interrupt, the guest main thread was sampled in `0x823B34A0`, the previously identified retail ring-queue wait helper; the run ended by external SIGINT without a guest trap or crash. This adds a current-artifact runtime observation but does not show that the wait was the only guest path during the run. See [the structured frontier evidence](../evidence/xbox360_frontier_82341198.json).

An 85.38-second follow-up sent six A/Start pulses and attached GDB once, without software breakpoints. The main guest thread was sampled in `sub_826F0380` called from `0x823A0310`, the retail timed-wait path; this snapshot did not read the live predicate bit. Host logs recorded 98 submissions of 14 captured draw packets and 860 source-0/sample-0 Copy/Convert entries, with no guest fault, but no pixel readback or menu/race state was captured. Four host CPUs were available for six guest CPUs, and the SDK emitted 6,144 scheduling warnings; whether that advisory affects progress remains unknown. See [the retail wait sample](../evidence/xbox360_linux_no_breakpoint_frontend_wait_20261025.json).

A fresh 40-second exact-XEX GDB probe hit all twelve generated entry points in the title's embedded PPC Bink section; helper `0x823A0998` executed 656 times without a recorded `SIGSEGV` or `SIGBUS`. The run used host executable SHA-256 `6a3ac722…`, the shared-memory-unlink runtime override SHA-256 `81117e5b…`, and plugin SHA-256 `badeb5c4…`; the harness interrupted it while the process was still running. This confirms guest Bink code execution, but does not show decoded pixels, identify the Bink texture/surface handoff, or demonstrate a frontend scene change. It supersedes an earlier unretained probe that was recorded as faulting at `0x823A0998`. See [the Bink guest-path evidence](../evidence/xbox360_bink_guest_path_20261025.json).

A 46.67-second exact-XEX trace then followed the live video wrapper to Bink object `0xE6795040`: the retail progress counter at `+0x0c` advanced to `0x100` by update 256 against a stable `+0x08` threshold of `0x119`, and the readiness and clock helpers each ran 280 times. This shows that the retail Bink timing path advances; it does not show decoded pixels, natural clip completion, or a menu transition. See the same [Bink guest-path evidence](../evidence/xbox360_bink_guest_path_20261025.json).

A separate 40-second exact-XEX GDB probe confirmed that both Bink manager callback slots dispatch guest functions `0x83068250` and `0x83068608` for all four manager entries. The callbacks are registered and execute as guest PPC code; this rules out an empty Bink callback slot in that run, while leaving the decoded-pixel and texture handoff unverified. See the same [Bink guest-path evidence](../evidence/xbox360_bink_guest_path_20261025.json).

A 38-second follow-up found four distinct downstream guest objects sharing vtable `0x820A8D28`. The Bink callbacks use its offsets 56 and 64, which point to guest functions `0x82B9C9F0` and `0x82B9DC78`; the latter forwards to `0x82BA9258`. This narrows the retail boundary after Bink, but the probe did not establish a texture upload, GPU command, or visible pixels. See the same [Bink guest-path evidence](../evidence/xbox360_bink_guest_path_20261025.json).

Follow-up probes dynamically entered `0x82B9C9F0`, `0x82B9DC78`, and `0x82BA9258` four times each. The callback compared a six-element array at guest stack address `0x7018F6F0`; three of four comparisons entered a transform callback whose vtable target at offset 12 is `0x82BB50E8`. That target adjusts into `0x82BB4F20`, whose child object uses `RtlEnterCriticalSection` and `RtlLeaveCriticalSection` wrappers. Three Bink-associated updates reached the retail allocator, returned non-null addresses, and returned `0` without a guest fault. This confirms progress through a guest resource-table wrapper; decoded pixels and GPU/pixel transfer remain unverified. See the same [Bink guest-path evidence](../evidence/xbox360_bink_guest_path_20261025.json).

A 45.16-second read-only GDB trace followed the Bink-associated callback into `0x82BA8DA8`. It compared six-element payloads with 24- or 48-byte spans and copied three changed payloads into guest buffers; the samples contain transform-like scalar data, including the IEEE-754 `1.0` bit pattern. This rules out treating that callback as the video-pixel handoff. The decoded frame buffer, GPU transfer and presentation remain unlocated. See the [callback payload trace](../evidence/xbox360_linux_bink_callback_payload_20261025.json) and [GDB probe](../tools/xbox360/trace_bink_callback_buffer.gdb).

A 75.33-second follow-up emitted six A/Start pulses and placed conditional breakpoints on the retail raw-mask getter `0x828B22B8` and changed-mask dispatcher `0x8230D398`. Neither observed an A/Start state under the probe conditions. This run did not capture the scene, so it narrows the next trace to frontend/boot progress without proving a title input failure or main-menu state. See [the frontend consumer probe](../evidence/xbox360_linux_gamepad_frontend_consumer_probe_20261025.json).

A separate exact-XEX vtable read ties those entries to the same observed controller object: slot `+0x98` is the per-frame `XamInputGetState`/edge-update path `0x82308E60`, slot `+0xBC` is raw-mask getter `0x828B22B8`, and slot `+0x54` is changed-button dispatcher `0x8230D398`. The retail update and edge accumulator were reached, but the bounded scene probe did not observe the action-dispatch slots consuming A/Start. This does not identify the active frontend scene or justify changing Linux input semantics. The exact vtable and probe hashes are recorded in the same [frontend consumer evidence](../evidence/xbox360_linux_gamepad_frontend_consumer_probe_20261025.json).

A 78-second follow-up sampled the exact retail wait predicate after the frontend's menu-background XML lookup. The guest expected cursor was `0x13dd` (5085), while the software-ring head/tail were 5077/5087 and the completion byte was `0x04`; the wait loop ran at least 2,816 times. The host log recorded 115 captured draw submissions and 1,116 Copy/Convert entries, then four missing `menu_background.xml` opens, with no guest fault. This confirms an outstanding retail queue cursor at the sample, but does not identify which component should advance it or prove the XML miss caused the wait. Preserve the predicate and queue semantics; no menu or race was reached. See the [read-only cursor capture](../evidence/xbox360_linux_retail_wait_cursor_20261025.json) and [reusable GDB trace](../tools/xbox360/trace_guest_ring_wait_cursor.gdb).

A second bounded run installed an unfiltered CPU hardware watchpoint on the sampled guest ring-head mapping (`0xb7af4000`, host mapping `0x1b7af4000`). It was not triggered during the approximately 23-second attached interval, which began at head/tail 1611/1619 and expected cursor 1613. Across the full run the host log recorded 89 submissions and 905 Copy/Convert entries, then four missing `menu_background.xml` opens and no later submission before shutdown. This negative sample cannot observe DMA/device writes or activity outside its attach window, so it does not identify the queue owner or establish a runtime defect. Keep the guest wait predicate unchanged. See the [bounded CPU write watch evidence](../evidence/xbox360_linux_ring_head_cpu_write_watch_20261025.json) and [read-only GDB probe](../tools/xbox360/trace_guest_ring_head_cpu_write.gdb).

A follow-up exact-XEX trace corrected the descriptor-head watch interpretation. The plugin writes the guest physical mapping at host address `0x217af4000`, while GDB's earlier watchpoint covered the separate virtual host mapping at `0x1b7af4000`; that watchpoint could miss the plugin writes. A physical-host hardware watchpoint then recorded 360 successive `EVENT_WRITE_SHD` head updates, and every observed value matched a simultaneous read through guest virtual address `0xb7af4000`. Retail wait samples saw the descriptor head advance from `3` to `0x2af` while the queue tail advanced from `21` to `695`. The earlier “descriptor stayed at 1” conclusion is superseded for this run. The completion byte remained `0x14`, but the queue progressed; this does not establish a predicate defect, menu/race entry, or visible output. See the [physical/virtual alias trace](../evidence/xbox360_linux_guest_ring_physical_virtual_alias_20261025.json).

A 70.35-second exact-XEX run with `--mnk_mode=true` emitted six Enter/Space pulses and captured the game window itself at 45 and 65 seconds. The two images are byte-identical and show the retail driving-safety warning; this run did not correlate its pulses to the retail XAM poll, so it does not prove that input was consumed. The final draw submission preceded four `menu_background.xml` open failures by 64 ms, and no later submission was logged, but this does not establish causality. The verified next P1 step is a same-run trace from retail input through the active frontend scene/action consumer. See the [window capture and run evidence](../evidence/xbox360_linux_safety_warning_screen_input_20261025.json).

A direct retail event-dispatch trace tied keyboard Enter to virtual target `0x82321198`. The generated body is the original one-instruction return, so this is a base no-op method, not an identified frontend action consumer. Preserve that guest behavior; the trace does not explain the active scene or establish menu/race progress. An earlier global-address probe was invalid and is excluded. See the [virtual-dispatch evidence](../evidence/xbox360_linux_keyboard_virtual_dispatch_20261025.json).

A fresh 72-second Linux run captured only the `nfs_shift` window while emitting five uinput A/Start pulses. The window changed from black to the SHIFT emblem and then to the driving-safety warning; captures at 32, 44, 56, and 68 seconds are byte-identical. This run had no same-run XAM trace, so it does not prove the pulses reached retail input or caused any transition. The host log recorded 100 indexed submissions, then four missing `menu_background.xml` opens and no later submissions; that timing does not establish causality. The main menu and race remain unverified. See the [window/input run evidence](../evidence/xbox360_linux_uinput_gamepad_window_20261025.json).

A read-only sweep then parsed every one of the 1,845 `.bff` archives under the exact retail game root with no index/range failures. None contains either requested `tracks/_data/{instances,static}/scenes/menu_background.xml` member or any `scenes/menu_background` path. Nearby packaged assets exist under different paths (`gui/menu_background/menu_background.sgx/.enx`, `lights.xml`, and `defaultcamera.xml`); the evidence does not establish they substitute for the absent XML. Combined with the traced parent return of success, this rules out an archive-member alias as a justified fix, while leaving the downstream frontend transition unresolved. See the [complete archive sweep](../evidence/xbox360_linux_menu_background_archive_sweep_20261025.json).

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
