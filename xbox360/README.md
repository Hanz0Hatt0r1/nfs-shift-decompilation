# Xbox 360 primary port workspace

This directory is reserved for **Need for Speed: SHIFT Xbox 360 retail** work via [ReXGlue](https://github.com/rexglue/rexglue-sdk).

**Current state: the exact retail title is not playable yet.** The latest 180.01-second Linux AMD64 run used the exact retail XEX (SHA-256 8c86a34f…), the P1 host (6a3ac722…), ReXGlue runtime (127181ad…), and P2 plugin (dec87581…). The game stayed live, but PID-scoped window captures alternated between the driving-safety warning and a black viewport after 44 A/Start uinput edges. The GPU ring worker consumed through guest RPTR 0x1F1F; no guest faults or Vulkan frame-refresh failures occurred. Same-run frontend input consumption, main menu, and offline race remain unverified. Vulkan 1.1, Linux ARM64, and Android ARM64 are not validated. See [latest exact-XEX ringtrace evidence](../evidence/xbox360_linux_ringtrace_frontend_followthrough_20261026.json). Game files, raw logs, and captures stay outside Git.

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

Trace the retail producer/completion callback and scheduling path for the current software-queue wait, then verify main-menu entry and an offline race. Do not change the retail predicate or infer a fatal blocker from the missing `menu_background.xml` opens: the observed retail parent stores the child result and returns success. The current Linux AMD64 runtime/build is external to Git; evidence records executable, runtime, plugin and XEX hashes. Vulkan 1.1-only and Android ARM64 compatibility still need separate exact-XEX runs.
