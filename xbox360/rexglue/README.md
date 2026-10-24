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

Eighteen missing retail entries are recorded in [the override snippet](nfs_shift_retail_function_overrides.toml). ReXGlue codegen and the Linux runtime build accept the complete 68-byte dispatcher at `0x82341198`; its exact branch paths and registered tail targets are preserved in [the capture evidence](../../evidence/xbox360_frontier_82341198.json). The rebuilt binary entered `xstart` but did not reach `0x82341198` during a 180-second controlled run, so execution of the override is unverified. An earlier binary executed the 60-byte conditional dispatcher at `0x823270D0` and then trapped at `0x82341198`. The `--no-async_shader_compilation` diagnostic removes the placeholder-skip warning and creates pipeline states synchronously. A later exact-XEX Linux run now captures presenter submission 10 with the original SHIFT loading splash; see [the 2026-10-25 evidence](../../evidence/xbox360_linux_retail_splash_validation_20261025.json). This proves one visible retail frame, not sustained rendering or frontend/race execution. A newer P2 plugin build read back opaque black at submission 200; the distinct binaries do not establish a transition. See [that exact-XEX record](../../evidence/xbox360_linux_retail_frame200_black_20261025.json). Focused regressions cover captured instruction bytes and override entries; they do not prove the retail dispatcher executes.

## Renderer note

The Linux host now enables `VK_EXT_swapchain_maintenance1` together with its required surface-maintenance instance extensions and completes the retail splash run without Vulkan validation VUIDs. The complete device capability requirements for **Vulkan 1.1** and SHIFT have **not** been proven; a newer API/extension cannot be presumed available on a Vulkan 1.1-only Android GPU. Track this in gate X6.

Upstream SDK build targets for Linux ARM64 do not alone establish Android application or SHIFT game compatibility. Gate X5 requires original-game execution on each target.

See [migration plan](../../docs/XBOX360_REXGLUE_MIGRATION.md) and [gate ledger](../../coordination/xbox360_rexglue_status.json).
