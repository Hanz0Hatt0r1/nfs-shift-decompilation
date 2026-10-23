# Development instructions — Xbox 360 / ReXGlue primary

Effective 2026-10-22: **Xbox 360 retail is the primary executable being ported.** ReXGlue ahead-of-time PowerPC→C++ and its Xbox 360 runtime/Xenos Vulkan stack are the first implementation path. Linux is the bring-up target; Android/ARM64 is the eventual product. Vulkan 1.1 remains a hard compatibility gate until explicitly revised with evidence.

## Authority and current state

- Read [ROADMAP.md](ROADMAP.md), [docs/XBOX360_REXGLUE_MIGRATION.md](docs/XBOX360_REXGLUE_MIGRATION.md) and [coordination/xbox360_rexglue_status.json](coordination/xbox360_rexglue_status.json) before selecting new Xbox work.
- **No `default.xex` is hash-locked, no SHIFT Xbox 360 recompilation or startup is proven.** Do not use PC corpus coverage, PC host frames or standalone Vulkan smoke tests as Xbox results.
- Xbox original binary/runtime evidence governs Xbox-specific behavior; PC 1.02 may be used for cross-version corroboration only after identity and semantic agreement are demonstrated.
- Source identities and reproducible tool revisions are mandatory; generated game code, retail game images, asset dumps and raw captures remain outside Git.
- Do not equate function/codegen coverage with behavioral parity, fabricated state with initialization, or synthetic rendering with a retail game draw.

## Workstreams and first blockers

- `X360-input`: retail XEX/title/build identity, asset inventory, source hash lock.
- `X360-recompiler`: pinned ReXGlue integration, XEX/PPC instruction coverage, build reproducibility.
- `X360-runtime`: original entrypoint, Xbox 360 kernel imports, threading, synchronization, file/content services.
- `X360-render`: game Xenos command path → Vulkan, shader and format compatibility, Vulkan 1.1 verification.
- `X360-platform`: Linux x86-64/ARM64 and Android ARM64 platform integration.

Before writing code answer: **Which exact open Xbox gate (X0–X6) does this change advance, and what observable proof will close it?**

The old PC/playable-slice P1/P2/P3 ownership labels and coordination JSON remain valid *within their historical PC workstreams only*. Do not rewrite generated PC status to describe the Xbox effort; see [archived process instructions](docs/PC_PLAYABLE_SLICE_PROCESS_20261022.md). Existing PC PRs remain subject to their original compatibility/test contracts.

## Branch / PR and test protocol

1. Fetch fresh `main` and check for existing PRs touching the same gate.
2. Work in a focused branch; one canonical PR per blocker, at most one stacked successor; do not force-push over someone else's work.
3. PR fields: `LANE`, `BLOCKER`, `INPUT`, `OUTPUT`, `CONSUMER`, `GATES_CHANGED`, `LIMITS`, `TESTS`, `SUPERSEDES`, `NEXT_OWNER`, `NEXT_STEP`.
4. A green build proves only the stated path. Record hashes, executed commands, target OS/architecture/GPU, observed outcomes, limitations and negative checks.
5. Run the relevant CI/CTest/pytest checks; keep unsupported gates explicitly false. Do not weaken existing PC checks during migration.
6. Re-read fresh `main` before merge. Merge only after required checks pass; avoid deleting or relocating legacy code before the new path has earned its gates.
7. Keep new workflows in stable reusable families; do not create phase-numbered workflow files.

## Git content policy

Never commit Xbox disc images, XEX binaries, extracted retail archives, generated copyrighted game translations, private user files or large runtime captures. `.gitignore` is only a convenience: review tracked content before committing. ReXGlue is an external SDK; pin version, track license and use a dependency integration policy rather than vendoring its code without review.
