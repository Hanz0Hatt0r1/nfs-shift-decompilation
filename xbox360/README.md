# Xbox 360 primary port workspace

This directory is reserved for **Need for Speed: SHIFT Xbox 360 retail** work via [ReXGlue](https://github.com/rexglue/rexglue-sdk).

**Currently this is a skeleton, not a working game build.** No title-specific XEX, ReXGlue config, PPC output, Vulkan gameplay or Android package is checked into the repo.

## Work areas

- [`rexglue/`](rexglue/README.md) — external SDK dependency, pinning and preflight approach.
- [Migration design](../docs/XBOX360_REXGLUE_MIGRATION.md) — boundaries and gates.
- [Status ledger](../coordination/xbox360_rexglue_status.json) — evidence-backed milestone states.

Expected future directories (create only with proven content): `analysis/` for metadata-only XEX reports; `runtime/` for SHIFT-specific Xbox service adapters; `render/` for verified Xbox GPU integration; `platform/` for host-specific glue; `tests/` for exact regression fixtures. Keep files and conventions aligned with ReXGlue's actual pinned CLI/API once tested.

## Required first input

An independently obtained original Xbox 360 retail game dump **kept outside Git**, including `default.xex` and the files it actually references. Record SHA-256, title/build ID and provenance, but do not upload or commit copyrighted binaries, extracted assets or generated translations.

The PC `SHIFT.exe` supplied for the legacy workstream is **not** a substitute for `default.xex`.

## First proof

Run the pinned upstream analyzer/compiler on the original XEX and store a textual result reporting: input hash, SDK commit, recognized code/functions, import/API dependencies, errors and next blocker. Until then X0/X1 remain open; no project-specific build command is presented as working.
