# Xbox 360 primary port workspace

This directory is reserved for **Need for Speed: SHIFT Xbox 360 retail** work via [ReXGlue](https://github.com/rexglue/rexglue-sdk).

**Current state: the exact retail title is not playable yet.** A 300.56-second Linux x86_64 run used retail `default.xex` SHA-256 `8c86a34f…`, P1 host/runtime hashes `6a3ac722…`/`6c56ca97…`, and P2 plugin SHA-256 `77120189…`. PID-scoped captures showed the driving-safety warning at 80, 215 and 300 seconds; six A/Start uinput pulses were emitted, but this run did not trace whether the retail frontend consumed them. No main-menu UI or race appeared. The title remained live until the harness sent SIGINT and exited 0; no guest fault was recorded. The renderer log contains one frame-refresh failure, whose cause is not established as the frontend stall. See [the latest exact-runtime interactive evidence](../evidence/xbox360_linux_exact_runtime_interactive_300s_20261027.json). Game files, raw logs, and captures stay outside Git.

An earlier 113.45-second Linux x86_64 run used P1 runtime `d8faeb39…` and a P2 renderer built from commit `296be17f…` (plugin SHA-256 `0ccbeab6…`). Its captures were mostly black after startup. The renderer logged eight mixed 4x-to-1x depth/stencil frame-refresh failures, but their causal role was unproven. See [that exact-XEX/P2 frontend evidence](../evidence/xbox360_linux_current_p2_296be_frontend_followthrough_20261027.json).

A previous 145.535-second no-input run used the same exact XEX and P1 host/runtime with the Linux plugin built from P2 source commit `9afec9ea…` (SHA-256 `01a2908c…`). It showed a dark viewport with no menu UI; one mixed-sample frame-refresh failure was recorded. See [the no-input follow-through evidence](../evidence/xbox360_linux_current_p2_auto_frontend_followthrough_20261027.json).

An earlier 180.01-second Linux AMD64 run used a different mapped runtime/plugin pair and observed the GPU ring worker consume through guest RPTR 0x1F1F. Its PID-scoped window captures alternated between the driving-safety warning and a black viewport after 44 A/Start uinput edges. See [the ringtrace evidence](../evidence/xbox360_linux_ringtrace_frontend_followthrough_20261026.json).

An earlier 53.4-second read-only GDB run with the shader-cache P2 plugin sampled the main guest thread in retail queue wait `0x823B34A0`: target 4975 sat between head 4967 and tail 4977, with completion mask `0x02` clear. The graphics worker was asleep in a condition-variable wait in that snapshot. This narrows the frontier but does not identify the missing producer or prove a P1/P2 defect. See [the retail wait evidence](../evidence/xbox360_linux_retail_wait_shader_cache_20261026.json).

A separate 40-second exact-XEX run tested the ReXGlue scheduler warning rate limit from [SDK PR #534](https://github.com/rexglue/rexglue-sdk/pull/534): the warning appeared once, 935 Copy/Convert entries were accepted, and no guest fault occurred. The game remained live until SIGINT. This confirms warning-volume reduction only; there was no pixel capture and no proof that warning spam caused the frontend stall. See [scheduler warning evidence](../evidence/xbox360_linux_scheduler_warning_limit_20261025.json).

## Work areas

- [`rexglue/`](rexglue/README.md) — external SDK dependency, pinning and preflight approach.
- [Migration design](../docs/XBOX360_REXGLUE_MIGRATION.md) — boundaries and gates.
- [Status ledger](../coordination/xbox360_rexglue_status.json) — evidence-backed milestone states.

Expected future directories (create only with proven content): `analysis/` for metadata-only XEX reports; `runtime/` for SHIFT-specific Xbox service adapters; `render/` for verified Xbox GPU integration; `platform/` for host-specific glue; `tests/` for exact regression fixtures. Keep files and conventions aligned with ReXGlue's actual pinned CLI/API once tested.

## Input record

The user-provided retail `default.xex` is kept outside Git. Its SHA-256, title ID, media ID and build metadata are recorded in the gate ledger and [preflight evidence](../evidence/xbox360_rexglue_preflight_20261022.md). Do not upload or commit copyrighted binaries, extracted assets or generated translations.

The PC `SHIFT.exe` supplied for the legacy workstream is **not** a substitute for `default.xex`.

## Next proof
A read-only exact-XEX trace records the retail Bink counter reaching target 0x119; the follow-up confirms `0x82E2C5A8` and scene update `0x82DDC6F0` return success and advance the scene counter before `0x82E2CD10` takes the child-completion path. This does not identify the next frontend state; see the [Bink completion evidence](../evidence/xbox360_linux_bink_completion_followthrough_20261027.json). The [PM4 callback crosswalk](../evidence/xbox360_linux_pm4_irq_worker_counter_20261027.json) matches 128 renderer interrupt records to the retail handler and follows 823 later queue publications through 823 worker executions. It also records a worker counter wrap whose intended signed meaning remains unresolved, so no scheduler patch was made. Next, trace the counter's readers and the frontend queue predicate around the callback-target switch, then verify controller input after Bink completion. Preserve retail event, queue, and input semantics. These event and worker counts do not prove a visible menu or race. The mixed-sample target-layout refresh failure remains in Process 2; its causal role in the black viewport is unproven. Do not treat missing menu_background.xml opens as fatal: the retail parent stores the child-loader result and returns success. The current Linux x86_64 runtime/build is external to Git; evidence records executable, runtime, plugin and XEX hashes. Vulkan 1.1-only and Android ARM64 compatibility still need separate exact-XEX runs.
