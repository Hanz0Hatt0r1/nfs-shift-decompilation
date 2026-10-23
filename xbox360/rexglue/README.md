# ReXGlue SDK integration policy

Upstream: https://github.com/rexglue/rexglue-sdk

ReXGlue is **not vendored or bundled** by this migration. The SDK is evolving and may have breaking changes; pin an exact upstream commit and audit its licenses/dependencies before integrating code into this repository.

## Preconditions

1. Verify and hash-lock the Xbox 360 SHIFT `default.xex` (no proprietary bytes in Git).
2. Select a specific upstream ReXGlue SDK revision and record its commit SHA, compiler version, platform and CLI/config syntax from that revision.
3. Produce a reproducible real-game XEX parsing and PPC→C++ lowering report. Keep generated game code and SDK build outputs outside Git.
4. Enumerate unresolved functions, imports, relocations, indirect targets, vector/FPU semantics, memory/endianness and initialization dependencies.
5. Only then define the first SHIFT-specific build target / configuration and host integration.

## Renderer note

ReXGlue has Xenos/Vulkan implementation components, but the complete device capability requirements for **Vulkan 1.1** and for SHIFT have **not** been proven. A newer API/extension cannot be presumed available on a Vulkan 1.1-only Android GPU. Track this in gate X6.

Upstream SDK build targets for Linux ARM64 do not alone establish Android application or SHIFT game compatibility. Gate X5 requires original-game execution on each target.

See [migration plan](../../docs/XBOX360_REXGLUE_MIGRATION.md) and [gate ledger](../../coordination/xbox360_rexglue_status.json).
