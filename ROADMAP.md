# Need for Speed: SHIFT — Xbox 360 / ReXGlue-first roadmap

**Adopted 2026-10-22.** The default development lane is now Xbox 360 retail → ReXGlue PowerPC AOT → Linux → Android ARM64. The existing PC 1.02 recompilation is retained for reference, verification and targeted maintenance, not deleted or represented as Xbox progress.

The retail Xbox 360 guest boots through ReXGlue on Linux and reaches the **Main Menu setup screen**, where it stalls; the game is not playable. X0 input identity is verified and the boot chain is proven end-to-end on both the Xenos and native Vulkan plugins, but the menu background renders black and the frontend is never entered. The two open blockers are now documented at file-and-line precision: the `MainMenu` scene gate that is never cleared (P1) and the unresolved draw packets that abort every menu frame (P2).

## Decision gates

| Gate | Acceptance evidence | Current status |
| --- | --- | --- |
| X0 — retail input identity | User-owned `default.xex`, SHA-256, title/build identification, external asset inventory | **Verified** — `8c86a34f…`, title `454108B4`, media `60DAC9C5`, XEX 0.0.0.3; hash independently recomputed 2026-10-30. Game bytes remain outside Git |
| X1 — ReXGlue feasibility | Pinned SDK revision; recorded XEX parse, PPC function/codegen coverage, imports and unresolved exceptions | In progress — ReXGlue 0.10.0 + fork `32afce4e…`; 505 generated units; 18 function-entry overrides. Open: unresolved branch `0x826F0E60`→`0x826FF380`, `float16_4` warning, and **T-PIN** (see below) |
| X2 — Linux link/boot | Recompiled executable links for Linux x86-64, reaches original guest entrypoint with deterministic logs | **Effectively met** — retail boot chain (Bink 281/281 → language select → EA logo → disclaimer) reaches Menu Setup state 2 on both backends, 20 update ticks. Not marked verified because gate closure requires the frontend/race evidence chain in one recorded run set |
| X3 — real GPU work | Original Xenos commands reach Vulkan; first measured non-synthetic retail frame | In progress — retail splash/logo pixels read back on Linux x86-64 (59,101 non-black px) and Android/Mali-G76. Menu background **black**: 24 unresolved draw packets + shader opcode 7 (`docs/P2_RENDER_UNRESOLVED_DRAW_PLAN_20261030.md`) |
| X4 — playable Linux | Original frontend, selectable offline race, input, audio and sustained game loop, with evidence | **Not reached** — exact blocker: `MainMenu` scene gate `scene+8` set once, never cleared (`sub_82DD8FF8` zero entries); GUI queue enqueue breakpoints never fire without a positive control; `sub_822FDCE0` dispatcher never called (`docs/P1_FRONTEND_FRONTIER_PLAN_20261030.md`) |
| X5 — portability | Linux ARM64 build/runtime validated; Android ARM64 packaging, input, audio, lifecycle validated | In progress — Android ARM64 graphics plugin builds and passes renderer checks on Mali-G76; full APK install blocked by `INSTALL_FAILED_INSUFFICIENT_STORAGE`; no in-game Android frame |
| X6 — Vulkan 1.1 | Explicit capability inventory and successful native execution on a Vulkan 1.1 device without assuming 1.2/1.3 | In progress — hard requirements `independentBlend`, `fragmentStoresAndAtomics`, `vertexPipelineStoresAndAtomics`; native renderer and Android probe now request 1.1 explicitly (PR #2157/#2156). No retail frame yet on a 1.1-only device |

The gate machine record is [coordination/xbox360_rexglue_status.json](coordination/xbox360_rexglue_status.json). Mark a gate verified only with an independently checkable evidence path, revision and observed result. SDK compilation alone does not prove SHIFT launches.

## Planned delivery order

1. **Input intake:** establish hashes, build/region/title identification, XEX imports, asset container list and lawful local extraction. Keep proprietary bytes out of Git.
2. **SDK pin + compiler preflight:** select and freeze a ReXGlue version, analyze XEX and generate a function-coverage/import summary. No hand-written fake stubs to advance a gate.
3. **First Linux runtime:** minimal Xbox 360 kernel/bootstrap adapter and original execution trace on x86-64. Classify missing services against XEX callsites.
4. **Xenos/Vulkan:** use ReXGlue's existing renderer as the starting point; verify shader translation, texture formats, render targets, synchronization and the Vulkan 1.1 extension/feature budget. Do not transplant PC D3D9 state as if it were Xenos.
5. **Gameplay proof:** frontend → user input → offline race → continuous simulation/renderer and audio. Compare against original Xbox execution when possible; use the PC path as corroboration only where versions demonstrably agree.
6. **Portable release path:** prove Linux ARM64 and Android ARM64 separately; document graphics-driver constraints, asset loading, input, audio, lifecycle and performance.
7. **Stabilization:** repeatable asset provenance, regression captures, portability tests, saved games, packaging and third-party license review.

## Open work (2026-10-30)

Ordered by what actually unblocks the next gate. Each item names the document that carries its evidence.

| # | Task | Why it is next | Lane |
| --- | --- | --- | --- |
| **T-PIN** | Reconcile every pinned artifact onto one SDK commit and re-verify | The pinned plugin came from SDK `b3648b0`, five commits behind fork HEAD `32afce4`, in exactly the presentation/memory subsystems under test. Until this closes, "reproducible build" is a claim the ledger itself marks unverified. | Build pins |
| **T-P2-a** | Gate draw readiness on a complete render-target mask, not `draw_register_valid_mask != 0` | 24 packets are declared register-ready while surface/color/depth/color_mask are all zero. The file already has the correct grouped-bit idiom for clears. | P2 |
| **T-P1-a** | Add a positive control for the menu GUI queue enqueue breakpoints | "0 enqueues" is an armed-but-unproven negative until something proves the breakpoints fire. | P1 |
| **T-P1-b** | Find the caller that should invoke the scene-gate clear `sub_82DD8FF8` | The gate is set once and never cleared; six hypotheses and a v119 capture design are already written. | P1 |
| **T-P4-a** | Census the `float16_4` warning sites and validate the operand encodings | Silent numeric drift inside an implemented handler; cross-platform agreement cannot detect it. | P4 |
| **T-P4-b** | Close the unresolved branch target `0x826F0E60`→`0x826FF380` | Loud `REX_FATAL` rooted in function-graph discovery, not instruction semantics. | P4 |
| **T-X5** | Get the APK installed on the ARM64 device | Every Android gate measurement is blocked on storage, not on code. | X5 |

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
