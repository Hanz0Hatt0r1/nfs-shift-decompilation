# Xbox 360 primary port workspace

This directory is reserved for **Need for Speed: SHIFT Xbox 360 retail** work via [ReXGlue](https://github.com/rexglue/rexglue-sdk).

**Current state: the exact retail title is not playable yet.** A 113.45-second Linux x86_64 run used retail `default.xex` SHA-256 `8c86a34f…`, P1 host/runtime hashes `6a3ac722…`/`d8faeb39…`, and the Linux renderer built from P2 commit `296be17f…` (plugin SHA-256 `0ccbeab6…`). A target-window capture showed the retail SHIFT loading screen before A/Start pulses; all later captures were mostly black with no menu UI. The host exited 0 only after the capture harness sent SIGINT. The renderer logged eight 1280x720 frame-refresh failures because mixed 4x-to-1x depth/stencil preservation requires an enabled resolve capability. It also logged 935 accepted Copy/Convert operations and 8,804 completed `COHER_STATUS_HOST` waits; these counts do not prove game progress. Four `menu_background.xml` misses were observed, but their causal role remains unproven. The game has not reached a verified retail main menu or offline race. See [latest exact-XEX/P2 frontend evidence](../evidence/xbox360_linux_current_p2_296be_frontend_followthrough_20261027.json). Game files, raw logs, and captures stay outside Git.

A newer 145.535-second no-input run used the same exact XEX and P1 host/runtime with the Linux plugin built from P2 source commit `9afec9ea…` (SHA-256 `01a2908c…`). The 30-second target-window capture showed a bright startup/loading graphic; captures at 60, 90, 120 and 145 seconds showed a black/dark viewport with no menu UI. The host remained live until harness SIGINT and exited 0. Its log recorded 497 accepted Copy/Convert entries, 10,407 completed `COHER_STATUS_HOST` waits, zero guest faults, and one 13-draw frame-refresh failure for mixed 4x-to-1x depth/stencil preservation without an enabled resolve capability. The single renderer failure is not proven to cause the black output, and the counters are not proof of game progress. The log contains no Bink/movie path strings; that does not prove the retail movie asset was not accessed. No input, main-menu UI or offline race was observed. See [the no-input follow-through evidence](../evidence/xbox360_linux_current_p2_auto_frontend_followthrough_20261027.json).

An earlier 180.01-second Linux AMD64 run used a different mapped runtime/plugin pair and observed the GPU ring worker consume through guest RPTR 0x1F1F. Its PID-scoped window captures alternated between the driving-safety warning and a black viewport after 44 A/Start uinput edges. See [the ringtrace evidence](../evidence/xbox360_linux_ringtrace_frontend_followthrough_20261026.json).

A later 53.4-second read-only GDB run with the shader-cache P2 plugin sampled the main guest thread in retail queue wait `0x823B34A0`: target 4975 sat between head 4967 and tail 4977, with completion mask `0x02` clear. The graphics worker was asleep in a condition-variable wait in that snapshot. This narrows the current frontier but does not identify the missing producer or prove a P1/P2 defect. See [the current retail wait evidence](../evidence/xbox360_linux_retail_wait_shader_cache_20261026.json).

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
A read-only exact-XEX trace now records the retail Bink counter reaching target 0x119. Next, trace 0x82E2CD10 and 0x82E2C5A8 return values and object+356 in 0x82DDC6F0 to identify the next child and frontend transition; see the [Bink frontier evidence](../evidence/xbox360_linux_bink_transition_frontier_20261027.json). Preserve retail queue, input, and movie semantics. The mixed-sample target-layout refresh failure remains in Process 2; its causal role in the black viewport is unproven. Do not infer game progress from submission counters or treat the missing menu_background.xml opens as fatal: the retail parent stores the child-loader result and returns success. The current Linux x86_64 runtime/build is external to Git; evidence records executable, runtime, plugin and XEX hashes. Vulkan 1.1-only and Android ARM64 compatibility still need separate exact-XEX runs.
