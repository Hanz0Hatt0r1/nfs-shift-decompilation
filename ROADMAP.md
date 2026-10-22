# Need for Speed: SHIFT — Xbox 360 / ReXGlue-first roadmap

**Adopted 2026-10-22.** The default development lane is now Xbox 360 retail → ReXGlue PowerPC AOT → Linux → Android ARM64. The existing PC 1.02 recompilation is retained for reference, verification and targeted maintenance, not deleted or represented as Xbox progress.

The immediate goal is to **prove feasibility**, not claim the port has begun executing. Status: **no verified SHIFT Xbox 360 input, recompiled executable or gameplay**.

## Decision gates

| Gate | Acceptance evidence | Current status |
| --- | --- | --- |
| X0 — retail input identity | User-owned `default.xex`, SHA-256, title/build identification, external asset inventory | Blocked: no verified XEX input |
| X1 — ReXGlue feasibility | Pinned SDK revision; recorded XEX parse, PPC function/codegen coverage, imports and unresolved exceptions | Not started |
| X2 — Linux link/boot | Recompiled executable links for Linux x86-64, reaches original guest entrypoint with deterministic logs | Not started |
| X3 — real GPU work | Original Xenos commands reach Vulkan; first measured non-synthetic retail frame | Not started |
| X4 — playable Linux | Original frontend, selectable offline race, input, audio and sustained game loop, with evidence | Not started |
| X5 — portability | Linux ARM64 build/runtime validated; Android ARM64 packaging, input, audio, lifecycle validated | Not started |
| X6 — Vulkan 1.1 | Explicit capability inventory and successful native execution on a Vulkan 1.1 device without assuming 1.2/1.3 | Not started |

The gate machine record is [coordination/xbox360_rexglue_status.json](coordination/xbox360_rexglue_status.json). Mark a gate verified only with an independently checkable evidence path, revision and observed result. SDK compilation alone does not prove SHIFT launches.

## Planned delivery order

1. **Input intake:** establish hashes, build/region/title identification, XEX imports, asset container list and lawful local extraction. Keep proprietary bytes out of Git.
2. **SDK pin + compiler preflight:** select and freeze a ReXGlue version, analyze XEX and generate a function-coverage/import summary. No hand-written fake stubs to advance a gate.
3. **First Linux runtime:** minimal Xbox 360 kernel/bootstrap adapter and original execution trace on x86-64. Classify missing services against XEX callsites.
4. **Xenos/Vulkan:** use ReXGlue's existing renderer as the starting point; verify shader translation, texture formats, render targets, synchronization and the Vulkan 1.1 extension/feature budget. Do not transplant PC D3D9 state as if it were Xenos.
5. **Gameplay proof:** frontend → user input → offline race → continuous simulation/renderer and audio. Compare against original Xbox execution when possible; use the PC path as corroboration only where versions demonstrably agree.
6. **Portable release path:** prove Linux ARM64 and Android ARM64 separately; document graphics-driver constraints, asset loading, input, audio, lifecycle and performance.
7. **Stabilization:** repeatable asset provenance, regression captures, portability tests, saved games, packaging and third-party license review.

## Stop / reconsider conditions

Reassess this strategy if ReXGlue cannot reliably process this exact XEX, the available Xbox 360 asset formats are incompatible with reasonable effort, or its Vulkan renderer cannot be made to work under the project's **Vulkan 1.1** requirement without unacceptable changes. Record a decision with evidence; do not silently increase the GPU requirement or declare the PC fallback deleted.

## Existing work preservation

- PC code: `native_runtime/`, `native_vulkan/`, `src/`, `tools/`, `tests/`, `evidence/`, plus importer tooling, remains intact.
- PC status and research are [indexed here](docs/PC_RECOMPILATION_STATUS.md).
- Historical full plans are [archived roadmap](docs/PC_RECOMPILATION_ROADMAP_20261022.md) and [archived README](docs/PC_RECOMPILATION_README_20261022.md).
- The retired standalone playable slice and its generated status remain **historical**, not the Xbox program tracker.
- Active legacy PRs may finish or be deferred on their own merits; do not mass-close them, reset CI evidence or force changes onto contributors.

## Work ownership

Use `X360-input`, `X360-recompiler`, `X360-runtime`, `X360-render` and `X360-platform` as workstream names in PRs and issue descriptions; PC reference tasks are `PC-reference`. Follow [PROCESS_INSTRUCTIONS.md](PROCESS_INSTRUCTIONS.md). The first merged Xbox change after this transition should establish **X0 input identity**; all subsequent success claims must cite its lock.
