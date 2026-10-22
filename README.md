# Need for Speed: SHIFT — Xbox 360 / ReXGlue port

**Primary direction (decision: 2026-10-22):** investigate the Xbox 360 retail version of Need for Speed: SHIFT as the source for an ahead-of-time PowerPC-to-C++ recompilation using [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk). Bring up the resulting native runtime on **Linux**, then target **Android/ARM64**. Keep **Vulkan 1.1** as a required compatibility target until a measured technical decision changes it.

**Status: migration scaffold only. Not playable.** No Xbox 360 `default.xex` has been identified/hash-locked in this repository, no SHIFT Xbox 360 recompilation is verified, and no Xbox guest frame, menu or race has been demonstrated. ReXGlue's general capabilities do not establish compatibility with this game or with Vulkan 1.1.

## Active workstreams

| Priority | Workstream | Scope |
| --- | --- | --- |
| **Primary** | [Xbox 360 + ReXGlue](xbox360/README.md) | Source identity, XEX analysis, PowerPC AOT recompilation, kernel/API integration, Xenos→Vulkan, Linux→ARM64→Android |
| **Reference / maintenance** | [PC 1.02 x86/P-code](docs/PC_RECOMPILATION_STATUS.md) | Preserve working tooling, evidence, regression tests and PC comparison captures; no longer the default blocker queue |
| **Shared, only after format verification** | Resources, scene/physics analysis and test tooling | Reuse version-neutral components where identities/endianness and semantics agree; do not assume PC/Xbox formats match |

## First milestone: reproducible Xbox 360 input and compiler preflight

1. Identify a legitimately obtained Xbox 360 retail `default.xex`, record its SHA-256, title/build identity and file inventory **outside Git**.
2. Pin a specific ReXGlue SDK revision and prove that this exact XEX can be analyzed and its PowerPC functions can be lowered.
3. Link and exercise a minimal Linux x86-64 executable; record kernel imports, exceptions, memory assumptions and first real blocker.
4. Connect real game GPU commands to the SDK's Xenos/Vulkan path. Verify **Vulkan 1.1** device requirements rather than assuming compatibility.
5. Reach the real frontend, a rendered frame and an offline race, then prove Linux ARM64 and Android ARM64 separately.

No step is credited based solely on synthetic fixtures, SDK demos, source-code presence or unrelated Xbox 360 games.

## Architecture

```text
Xbox 360 retail default.xex (user-owned, external to Git)
  -> hash-locked XEX/PowerPC analysis
  -> ReXGlue ahead-of-time C++ output
  -> ReXGlue Xbox 360 kernel/runtime and game-specific adapters
  -> original Xbox 360 Xenos GPU commands
  -> Vulkan renderer (Vulkan 1.1 compatibility gate)
  -> Linux x86-64 -> Linux ARM64 -> Android ARM64
```

The current PC executable and all existing Python/native tools remain available in this repo, but **they are not evidence that the Xbox 360 path runs**.

## Project entry points

- [New roadmap](ROADMAP.md) — primary milestones, blockers and exit criteria.
- [Migration architecture and safeguards](docs/XBOX360_REXGLUE_MIGRATION.md).
- [Xbox 360 workspace](xbox360/README.md) and [SDK integration policy](xbox360/rexglue/README.md).
- [Machine-readable Xbox migration status](coordination/xbox360_rexglue_status.json), checked by [the status validator](tools/xbox360/validate_status.py).
- [Preserved PC research status, source docs and archived roadmap](docs/PC_RECOMPILATION_STATUS.md).
- [Current development instructions](PROCESS_INSTRUCTIONS.md).

## Existing PC work (preserved)

The original PC 1.02 path includes a 41,538-function frozen x86 P-code corpus whose current snapshot is lowerable to C and linkable as a Linux ELF module; PE32 loading, guest Win32 services, native Vulkan smoke tests and extensive retail execution research are present. **This is not a complete PC game port.** Actual PC retail rendering, frontend and race were not demonstrated in the recompiled Linux runtime as of the archived status. The counts and probe claims refer **only to PC** and should not be reclassified as Xbox progress.

Use the [archived full README](docs/PC_RECOMPILATION_README_20261022.md) and [archived roadmap](docs/PC_RECOMPILATION_ROADMAP_20261022.md) for the prior rationale and technical evidence.

## Source and redistribution boundaries

Do not commit, redistribute or embed Xbox game binaries, disc images, extracted game content, generated copyrighted translations or personal captures. XEX identity records contain hashes and metadata only. ReXGlue, Xenia-derived code and other dependencies remain externally licensed projects; pin and audit dependencies before incorporation.
