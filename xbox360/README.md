# Xbox 360 primary port workspace

This directory is reserved for **Need for Speed: SHIFT Xbox 360 retail** work via [ReXGlue](https://github.com/rexglue/rexglue-sdk).

**Current state: the exact retail title reaches Language Select and the safety-warning presentation, then renders a black viewport; the game is not playable yet.** A 75-second Linux AMD64 run using the latest P2 plugin reached those states but did not show the main menu or a race. It logged 1,111 accepted Copy/Convert operations, no guest faults, and no Vulkan frame-refresh failures. A separate instrumented run observed 280 retail Bink update calls for a 281-frame video before the harness interrupted it; natural video completion and the following scene transition remain unproven. The main menu, offline race, Vulkan 1.1-only compatibility and Android execution remain open. Evidence: [post-video frontend probe](../evidence/xbox360_linux_post_video_frontend_probe_20261025.json), [earlier retail splash](../evidence/xbox360_linux_retail_frame10_current_plugin_20261025.json), [submission 200](../evidence/xbox360_linux_retail_frame200_black_20261025.json). Game files and captured pixels stay outside Git.

## Work areas

- [`rexglue/`](rexglue/README.md) — external SDK dependency, pinning and preflight approach.
- [Migration design](../docs/XBOX360_REXGLUE_MIGRATION.md) — boundaries and gates.
- [Status ledger](../coordination/xbox360_rexglue_status.json) — evidence-backed milestone states.

Expected future directories (create only with proven content): `analysis/` for metadata-only XEX reports; `runtime/` for SHIFT-specific Xbox service adapters; `render/` for verified Xbox GPU integration; `platform/` for host-specific glue; `tests/` for exact regression fixtures. Keep files and conventions aligned with ReXGlue's actual pinned CLI/API once tested.

## Input record

The user-provided retail `default.xex` is kept outside Git. Its SHA-256, title ID, media ID and build metadata are recorded in the gate ledger and [preflight evidence](../evidence/xbox360_rexglue_preflight_20261022.md). Do not upload or commit copyrighted binaries, extracted assets or generated translations.

The PC `SHIFT.exe` supplied for the legacy workstream is **not** a substitute for `default.xex`.

## Next proof

Trace the retail scene-manager path after the safety/Bink presentation and verify an offline race. Do not infer a fatal blocker from the missing `menu_background.xml` opens: the observed retail parent stores the child result and returns success. The current Linux AMD64 runtime/build is external to Git; evidence records executable, runtime, plugin and XEX hashes. Vulkan 1.1-only and Android ARM64 compatibility still need separate exact-XEX runs.
