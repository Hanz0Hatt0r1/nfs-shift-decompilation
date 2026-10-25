# Xbox 360 primary port workspace

This directory is reserved for **Need for Speed: SHIFT Xbox 360 retail** work via [ReXGlue](https://github.com/rexglue/rexglue-sdk).

**Current state: the exact retail title is not playable yet.** The latest 120.027-second Linux x86_64 run used the P2 handover plugin (commit `99cdd93a`, SHA-256 `e2679a4c…46736bf4`, Build ID `173c8c62…294fb8d`) and showed the retail safety warning in three sampled frames; the other six sampled frames had a black game viewport. The runtime accepted 1,103 Copy/Convert operations, then logged four `menu_background.xml` misses about 80 ms after its last accepted operation. There were no guest faults or Vulkan frame-refresh failures. This timing does not establish that the missing XML stopped rendering. The exact-XEX process stayed live for the full harness run, but the main menu and an offline race were not reached. Natural video completion, Vulkan 1.1-only compatibility and Android execution remain open. See [latest P2 handover run](../evidence/xbox360_linux_p2_handover_frontend_followthrough_20261025.json), [post-video frontend probe](../evidence/xbox360_linux_post_video_frontend_probe_20261025.json), [earlier retail splash](../evidence/xbox360_linux_retail_frame10_current_plugin_20261025.json), and [submission 200](../evidence/xbox360_linux_retail_frame200_black_20261025.json). Game files and captured pixels stay outside Git.

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

Trace the retail scene-manager path through the safety/Bink presentation and verify an offline race. Do not infer a fatal blocker from the missing `menu_background.xml` opens: the observed retail parent stores the child result and returns success. The current Linux AMD64 runtime/build is external to Git; evidence records executable, runtime, plugin and XEX hashes. Vulkan 1.1-only and Android ARM64 compatibility still need separate exact-XEX runs.
