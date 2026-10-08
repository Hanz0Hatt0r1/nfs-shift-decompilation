# Development process v2

This document defines how parallel work is selected, handed off, tested and merged for the first native Linux playable slice.

## Canonical live state

`evidence/playable_slice_three_process_execution.json` is the single source of truth for live project status.

Human summaries in `README.md`, `ROADMAP.md`, phase notes and PR descriptions are explanatory only. They must never override the canonical execution state when selecting work.

`coordination/PLAYABLE_SLICE_STATUS.md` is generated from the canonical execution state:

```bash
python tools/coordination/render_playable_slice_status.py --write
python tools/coordination/render_playable_slice_status.py --check
```

The coordination CI job verifies that the generated status is current and that provider counts, lane coverage and terminal smoke gates are internally consistent. The tool also warns when human summaries advertise a different phase. `--strict-human-docs` can be enabled once historical README/ROADMAP status text is cleaned up.

## Development lanes

The project keeps three semantic ownership domains but exposes the real parallel lanes explicitly in `coordination/lane_ownership.json`:

- `P1A-contact` — contact/collision retail proof and producer ownership.
- `P1B-control` — retail input -> drivetrain/wheel/control provenance.
- `P1D-camera` — retail camera-follow source, target dependency and ordering.
- `P2-runtime` — native physics/runtime consumption of positive retail contracts.
- `P3-integration` — resources, scene, Vulkan, bootstrap and final smoke.

The lane registry owns work boundaries, not live status. A queue state always comes from the canonical execution JSON.

## Work selection

Before substantial work:

1. Read fresh `main`.
2. Read `coordination/PLAYABLE_SLICE_STATUS.md`.
3. Pick a queue item owned by your lane whose state allows progress.
4. Answer: **Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**
5. Do not reopen a closed proof surface unless new evidence invalidates its assumptions.

Parallel work should prefer ready independent items. In particular, `P2.4` may proceed while `P2.3` is blocked on `P1.1`; Process 2 must not idle only because the first provider-reduction target is blocked.

## PR ownership and supersession

There should be one canonical PR per blocker and at most one stacked successor.

Every blocker-relevant PR uses:

```text
LANE:
BLOCKER:
INPUT:
OUTPUT:
CONSUMER:
GATES_CHANGED:
LIMITS:
TESTS:
SUPERSEDES:
NEXT_OWNER:
NEXT_STEP:
```

If a stronger PR supersedes another PR:

1. Preserve or transplant any unique evidence first.
2. State the superseding PR or merged contract in the old PR.
3. Close the superseded PR.
4. Do not keep multiple live branches attacking the same exact proof surface unless their evidence families are intentionally independent.

A negative proof that permanently removes a candidate is merge-worthy when it is exact, tested and monotonically narrows the blocker. A PR does not need to solve the entire parent blocker to be useful.

## Merge gate

Before merge:

- re-read fresh `main`;
- rebase or transplant rather than overwriting newer coordination state;
- required focused CI must be green;
- full/native/integration CI required by the touched subsystem must be green;
- no unsupported semantic gate may be promoted;
- provider count changes only when the complete external boundary is actually removed;
- generated coordination status must pass `--check`.

Self-merge is allowed after these gates pass.

## CI policy

Do not add new phase-numbered workflow files.

Prefer stable workflow families:

- `coordination`
- `evidence-fast`
- `CI`
- `linux-vulkan`
- subsystem/native integration workflows that are reused across phases

New phase-specific coverage should normally be expressed as pytest markers, CTest targets, workflow matrices or data-driven target lists inside a stable workflow. Existing historical phase-numbered workflows may be migrated incrementally when touched; migration must not weaken current gates.

## Progress metrics

Phase number is not the primary readiness metric.

Track:

- `active_external_provider_count`;
- `fun_00766510_p1_complete`;
- `retail_control_chain_complete`;
- `retail_camera_follow_ready`;
- `final_playable_smoke_currently_runnable`;
- `playable_slice_complete`.

The generated status page is the blocker burndown for these gates.

## External research inputs

Large proprietary or machine-generated research inputs remain outside Git.

Any input that can change semantic conclusions should be hash-pinned in the evidence contract that consumes it. Google Drive folders are storage/discovery locations, not semantic authority by themselves; exact executable/database/export hashes remain the reproducibility boundary.
