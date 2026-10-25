# ReXGlue SDK integration policy

Upstream: https://github.com/rexglue/rexglue-sdk

ReXGlue is **not vendored or bundled** by this migration. The SDK is evolving and may have breaking changes; pin an exact upstream commit and audit its licenses/dependencies before integrating code into this repository.

## Preconditions

1. Verify and hash-lock the Xbox 360 SHIFT `default.xex` (no proprietary bytes in Git).
2. The local diagnostic package is linked to official ReXGlue `v0.10.0` commit `f5337cdc947ff6d4c4196737e2c807a48f2a1fc2`; record the exact compiler/platform/CLI configuration in any future checked-in build integration.
3. Produce a reproducible real-game XEX parsing and PPC→C++ lowering report. Keep generated game code and SDK build outputs outside Git.
4. Enumerate unresolved functions, imports, relocations, indirect targets, vector/FPU semantics, memory/endianness and initialization dependencies.
5. Only then define the first SHIFT-specific build target / configuration and host integration.

## Current retail function override

Eighteen missing retail entries are recorded in [the override snippet](nfs_shift_retail_function_overrides.toml). ReXGlue codegen and the Linux runtime build accept the complete 68-byte dispatcher at `0x82341198`; its exact branch paths and registered tail targets are preserved in [the capture evidence](../../evidence/xbox360_frontier_82341198.json). The rebuilt binary entered `xstart` but did not reach `0x82341198` during a 180-second controlled run, so execution of the override is unverified. An earlier binary executed the 60-byte conditional dispatcher at `0x823270D0` and then trapped at `0x82341198`. The `--no-async_shader_compilation` diagnostic removes the placeholder-skip warning and creates pipeline states synchronously. A later exact-XEX Linux run now captures presenter submission 10 with the original SHIFT loading splash; see [the 2026-10-25 evidence](../../evidence/xbox360_linux_retail_splash_validation_20261025.json). This proves one visible retail frame, not sustained rendering or frontend/race execution. The current P2 plugin reproduces the splash at submission 10, while a separate run with the same exact binaries reads back opaque black at submission 200; these are not one continuous run. See [frame 10](../../evidence/xbox360_linux_retail_frame10_current_plugin_20261025.json) and [frame 200](../../evidence/xbox360_linux_retail_frame200_black_20261025.json). Focused regressions cover captured instruction bytes and override entries; they do not prove the retail dispatcher executes.

## Latest retail frontend probe

A 120.027-second exact-XEX run loaded the P2 handover Linux plugin from commit `99cdd93a92a580d562ca3f0c4c88e2e4a9d3b537` (SHA-256 `e2679a4ca54178a312af3f6cc7cc2ba0eb8dd562a8e730a32131068d46736bf4`, Build ID `173c8c62e2dea1cf2b5a8161003e6e63e294fb8d`) and the recorded ReXGlue runtime. `/proc/<pid>/maps` confirmed the expected plugin was loaded. Nine window-only captures alternate between the retail safety warning and a black game viewport; the exact-XEX process remained live until the harness stopped it. The runtime logged 1,103 accepted Copy/Convert operations, zero guest faults and zero Vulkan frame-refresh failures. Four `menu_background.xml` open failures appeared about 80 ms after the last accepted Copy/Convert, but this correlation does not prove the misses caused the black viewport or stopped guest submissions. The main menu and offline race were not reached. Full hashes, capture metadata and limitations are in the [latest P2 handover run evidence](../../evidence/xbox360_linux_p2_handover_frontend_followthrough_20261025.json). The run did not modify renderer or runtime source trees.

The exact `Franchise_Ident.bik` asset declares 281 frames and the guest Bink object had a frame target of `0x119`. The breakpoint trace observed 280 readiness, clock-update and video-wrapper calls; its last printed progress sample was `0x110` at hit 272 before SIGINT. Software breakpoints perturb timing, so natural movie completion and the next guest scene were not established. Continue at the retail scene-manager caller after the Bink wrapper stops, and capture the return/state transition around the first `menu_background.xml` miss. See [the post-video probe](../../evidence/xbox360_linux_post_video_frontend_probe_20261025.json). The SDK shared-memory unlink fix remains tracked separately in [ReXGlue SDK PR #4](https://github.com/Hanz0Hatt0r1/rexglue-sdk/pull/4); this local runtime hash is not the application's default runtime.

## Renderer note

The Linux host now enables `VK_EXT_swapchain_maintenance1` together with its required surface-maintenance instance extensions and completes the retail splash run without Vulkan validation VUIDs. The complete device capability requirements for **Vulkan 1.1** and SHIFT have **not** been proven; a newer API/extension cannot be presumed available on a Vulkan 1.1-only Android GPU. Track this in gate X6.

Upstream SDK build targets for Linux ARM64 do not alone establish Android application or SHIFT game compatibility. Gate X5 requires original-game execution on each target.

See [migration plan](../../docs/XBOX360_REXGLUE_MIGRATION.md) and [gate ledger](../../coordination/xbox360_rexglue_status.json).
