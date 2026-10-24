# Xbox 360 primary port workspace

This directory is reserved for **Need for Speed: SHIFT Xbox 360 retail** work via [ReXGlue](https://github.com/rexglue/rexglue-sdk).

**Current state: one retail loading-splash capture; the game is not playable yet.** The hash-locked XEX produced a non-black original logo/loading-bar readback in one Linux run. A newer renderer build produced an opaque-black submission-200 readback; the different binaries prevent treating the captures as a continuous transition. The main menu, offline race, Vulkan 1.1-only compatibility and Android execution remain open. Evidence: [splash](../evidence/xbox360_linux_retail_splash_validation_20261025.json), [frame 200](../evidence/xbox360_linux_retail_frame200_black_20261025.json). Game files and captured pixels stay outside Git.

## Work areas

- [`rexglue/`](rexglue/README.md) — external SDK dependency, pinning and preflight approach.
- [Migration design](../docs/XBOX360_REXGLUE_MIGRATION.md) — boundaries and gates.
- [Status ledger](../coordination/xbox360_rexglue_status.json) — evidence-backed milestone states.

Expected future directories (create only with proven content): `analysis/` for metadata-only XEX reports; `runtime/` for SHIFT-specific Xbox service adapters; `render/` for verified Xbox GPU integration; `platform/` for host-specific glue; `tests/` for exact regression fixtures. Keep files and conventions aligned with ReXGlue's actual pinned CLI/API once tested.

## Input record

The user-provided retail `default.xex` is kept outside Git. Its SHA-256, title ID, media ID and build metadata are recorded in the gate ledger and [preflight evidence](../evidence/xbox360_rexglue_preflight_20261022.md). Do not upload or commit copyrighted binaries, extracted assets or generated translations.

The PC `SHIFT.exe` supplied for the legacy workstream is **not** a substitute for `default.xex`.

## Next proof

Move the exact retail title from the captured loading splash into the real frontend, then verify an offline race. The current Linux AMD64 runtime/build is external to Git; the evidence records executable, runtime, plugin and XEX hashes. Vulkan 1.1-only and Android ARM64 compatibility still need separate exact-XEX runs.
