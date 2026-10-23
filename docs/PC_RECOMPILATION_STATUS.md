# PC recompilation / research archive

The PC retail 1.02 effort was the original execution target. On 2026-10-22, **Xbox 360 + ReXGlue** became the primary proposed path; this PC work is now a **reference/maintenance workstream**, not discarded.

## Preserved canonical snapshots

- [Full PC-era README, archived 2026-10-22](PC_RECOMPILATION_README_20261022.md): measured x86 P-code lowering, ELF loader, Win32 guest bridge, retail traces and resource tooling.
- [Full PC-era roadmap, archived 2026-10-22](PC_RECOMPILATION_ROADMAP_20261022.md): old milestones, bounded probes, open PC blockers and evidence links.
- [Original playable-slice coordination instructions, archived 2026-10-22](PC_PLAYABLE_SLICE_PROCESS_20261022.md): historical P1/P2/P3 work rules.

## Retained implementation and evidence

- `native_runtime/` — Linux guest PE32/P-code and native runtime.
- `native_vulkan/` and `src/graphics/d3d9/` — native Vulkan, D3D9 capture and bridge.
- `src/`, `shift_importer.py`, `BFF_TOOLS.md` — recovered resource formats, renderer and physics tooling.
- `tools/`, `tests/`, `evidence/` and `coordination/` — tooling, proofs, regression tests and historical state.

The PC snapshot states **41,538 frozen functions lowerable**; this is not 100% recovered game semantics or proof of a playable native Linux port. XEX/PPC function counts are a separate inventory and must never reuse the PC totals.

For any PC follow-up, keep the original PE32 hashes and exact evidence; for the new Xbox direction use the [new roadmap](../ROADMAP.md) and [migration plan](XBOX360_REXGLUE_MIGRATION.md).
