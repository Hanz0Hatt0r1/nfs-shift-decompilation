# Need for Speed: SHIFT — Xbox 360 / ReXGlue port

**Primary direction (decision: 2026-10-22):** investigate the Xbox 360 retail version of Need for Speed: SHIFT as the source for an ahead-of-time PowerPC-to-C++ recompilation using [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk). Bring up the resulting native runtime on **Linux**, then target **Android/ARM64**. Keep **Vulkan 1.1** as a required compatibility target until a measured technical decision changes it.

**Status: retail game boots to the Main Menu setup screen and stalls there; not playable.** The hash-locked Xbox 360 `default.xex` (`8c86a34f…`, title `454108B4`) runs through the retail boot chain — Bink videos (281/281), language select, EA logo, safety disclaimer — and reaches **Menu Setup state 2**, which it holds for 20 update ticks (~33 s) on **both** the Xenos plugin (`8b5abe7a…`) and the native Vulkan plugin (`fd615ada…`). Retail splash/logo pixels read back correctly on Linux x86-64 and on Android ARM64 (Mali-G76). The menu background is still **black**, and the frontend is **not reached**: the `MainMenu` scene gate at `scene+8` is set once and never cleared, and the menu GUI event queue is constructed and polled but its enqueue breakpoints never fire.

See [the gate ledger](coordination/xbox360_rexglue_status.json) for per-gate evidence and the three active lane plans: [P1 frontend](docs/P1_FRONTEND_FRONTIER_PLAN_20261030.md), [P2 renderer](docs/P2_RENDER_UNRESOLVED_DRAW_PLAN_20261030.md), [P4 codegen](docs/P4_PPC_CODEGEN_DIAGNOSTICS_PLAN_20261030.md).

**Reproducibility caveat — read before citing a pin.** Pinned artifacts are *hash-verified but not build-reproducible*. The pinned native plugin was produced from SDK `b3648b0`, an ancestor of the recorded fork HEAD `32afce4`; five commits separate them and they touch exactly the presentation and guest-memory subsystems the runtime depends on, so a rebuild at HEAD does not reproduce the pinned `.so`. `tools/xbox360/build/verify_pins.py` verifies hashes and prints `unverified_pins` on every run so a PASS cannot launder an unproven producer. Reconciling every artifact onto one SDK commit is open work (**T-PIN** in [ROADMAP.md](ROADMAP.md)). Current: 4 located artifacts hash-matched, 3 producer commits unresolved, retail XEX hash independently recomputed.

## Active workstreams

| Priority | Workstream | Scope |
| --- | --- | --- |
| **Primary** | [Xbox 360 + ReXGlue](xbox360/README.md) | Source identity, XEX analysis, PowerPC AOT recompilation, kernel/API integration, Xenos→Vulkan, Linux→ARM64→Android |
| **Reference / maintenance** | [PC 1.02 x86/P-code](docs/PC_RECOMPILATION_STATUS.md) | Preserve working tooling, evidence, regression tests and PC comparison captures; no longer the default blocker queue |
| **Shared, only after format verification** | Resources, scene/physics analysis and test tooling | Reuse version-neutral components where identities/endianness and semantics agree; do not assume PC/Xbox formats match |

## First milestone: reproducible Xbox 360 boot through a real frame

Where each step actually stands (nothing below is credited on fixtures, SDK demos, source-code presence or unrelated titles):

| Step | State |
| --- | --- |
| 1. Retail XEX identity recorded outside Git | **done**, X0 verified; hash recomputed 2026-10-30 |
| 2. Pinned SDK revision lowers this exact XEX | **partial**, X1 — 505 units generated, 2 codegen diagnostics open, SDK↔artifact pin reconciliation open (T-PIN) |
| 3. Linux x86-64 executable boots the retail guest | **done in substance**, X2 — boot chain reaches Menu Setup state 2 on both backends |
| 4. Real GPU commands reach the Vulkan path with 1.1 verified | **partial**, X3/X6 — splash renders and reads back; menu background black, 24 unresolved draw packets |
| 5. Real frontend, rendered frame, offline race, then ARM64/Android | **open**, X4 not reached / X5 partial — exact frontend blocker documented in the P1 plan |

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

## Active lanes (2026-10-30)

Each lane is a planning document whose claims name a file and line, or are marked **unknown**. None of them is a fix.

| Lane | Document | Question it must answer |
| --- | --- | --- |
| **P1 frontend** | [P1_FRONTEND_FRONTIER_PLAN_20261030.md](docs/P1_FRONTEND_FRONTIER_PLAN_20261030.md) | Why is the `MainMenu` scene gate never cleared, and why do the menu GUI queue's enqueue breakpoints never fire? Six hypotheses (H1–H6), a v119 capture design and red lines that forbid patching guest memory or forcing a predicate. |
| **P2 renderer** | [P2_RENDER_UNRESOLVED_DRAW_PLAN_20261030.md](docs/P2_RENDER_UNRESOLVED_DRAW_PLAN_20261030.md) | Why are draw packets 0–23 unresolved (`valid_mask=0x17038` with every render-target register zero) and what is shader control-flow opcode 7? Fix order matters: the frame aborts on packet 0, so opcode 7 is strictly downstream. |
| **P4 codegen** | [P4_PPC_CODEGEN_DIAGNOSTICS_PLAN_20261030.md](docs/P4_PPC_CODEGEN_DIAGNOSTICS_PLAN_20261030.md) | The `float16_4` warning sits inside a *fully implemented* handler (silent numeric drift, HIGH risk, undetectable by the shadow ladder), while the unresolved branch is a loud `REX_FATAL` in function-graph discovery. |
| **Build pins** | [XBOX360_BUILD_PINS_20261030.md](docs/XBOX360_BUILD_PINS_20261030.md) | Which SDK commit and which source commit produced this `.so`? Ledger + verifier; the honest answer today is "not fully known" (T-PIN). |
| **Capture reproducibility** | [XBOX360_V118_SCENE_GATE_RUNNER_20261030.md](docs/XBOX360_V118_SCENE_GATE_RUNNER_20261030.md) | How do you re-derive the v118 frontier numbers? A read-only analyser plus a 17-test regression that reproduces them from the raw run directories. |

Rebuild the frontier summary at any time:

```bash
python3 tools/xbox360/analyse_menu_setup_scene_gate_run_20261029.py <run-dir>
python3 tools/xbox360/build/verify_pins.py
python3 tools/xbox360/validate_status.py
```

## Existing PC work (preserved)

The original PC 1.02 path includes a 41,538-function frozen x86 P-code corpus whose current snapshot is lowerable to C and linkable as a Linux ELF module; PE32 loading, guest Win32 services, native Vulkan smoke tests and extensive retail execution research are present. **This is not a complete PC game port.** Actual PC retail rendering, frontend and race were not demonstrated in the recompiled Linux runtime as of the archived status. The counts and probe claims refer **only to PC** and should not be reclassified as Xbox progress.

Use the [archived full README](docs/PC_RECOMPILATION_README_20261022.md) and [archived roadmap](docs/PC_RECOMPILATION_ROADMAP_20261022.md) for the prior rationale and technical evidence.

## Source and redistribution boundaries

Do not commit, redistribute or embed Xbox game binaries, disc images, extracted game content, generated copyrighted translations or personal captures. XEX identity records contain hashes and metadata only. ReXGlue, Xenia-derived code and other dependencies remain externally licensed projects; pin and audit dependencies before incorporation.
