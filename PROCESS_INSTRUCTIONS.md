# Playable slice coordination instructions

The first native Linux playable slice uses three semantic ownership domains and five explicit parallel development lanes.

## Canonical live state

Do not select work from stale phase notes, README prose, historical roadmap text or old PR descriptions.

Machine-readable execution state:

[`evidence/playable_slice_three_process_execution.json`](evidence/playable_slice_three_process_execution.json)

Generated human-readable status, blocker burndown, provider count and parallel-ready work:

[`coordination/PLAYABLE_SLICE_STATUS.md`](coordination/PLAYABLE_SLICE_STATUS.md)

Development/merge rules:

[`coordination/DEVELOPMENT_PROCESS_V2.md`](coordination/DEVELOPMENT_PROCESS_V2.md)

Lane ownership:

[`coordination/lane_ownership.json`](coordination/lane_ownership.json)

Legacy detailed three-process instructions/prompts remain useful background but do not override the canonical execution state:

- [`docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md`](docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md)
- [`docs/PLAYABLE_SLICE_THREE_PROCESS_PROMPTS_V6.md`](docs/PLAYABLE_SLICE_THREE_PROCESS_PROMPTS_V6.md)

The mandatory pre-task question is:

> **Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

## Active lanes

```text
P1A-contact
  retail contact/collision proof, ABI, producer ownership and ordering

P1B-control
  retail input -> drivetrain/wheel/control producer provenance

P1D-camera
  retail camera-follow source, target dependency, ordering and freshness

        |
        v

P2-runtime
  native physics/runtime consumption of positive retail contracts

        |
        v

P3-integration
  exact resources, Silverstone/BMW scene, Vulkan, bootstrap and final smoke
```

The exact queue IDs owned by each lane are defined in `coordination/lane_ownership.json`. Their **live states** come only from the canonical execution JSON.

Lanes may advance in parallel on independent ready items. A blocked task must not idle an entire lane when another owned queue item is explicitly ready-to-consume.

Cross-lane handoffs are fail-closed. Unresolved semantic ownership is never transferred merely to keep another process busy.

## Task selection

Before substantial work:

1. read fresh `main`;
2. read `coordination/PLAYABLE_SLICE_STATUS.md`;
3. choose a queue item owned by your lane whose live state permits progress;
4. identify the exact playable-slice blocker it removes;
5. inspect existing merged contracts so closed proof surfaces are not rediscovered.

If current `main` advanced while you were working, re-evaluate the frontier before producing a PR.

## Branch and PR protocol

Prefer the lane-specific prefixes defined in `coordination/lane_ownership.json`.

Every blocker-relevant PR uses the repository PR template fields:

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

There should be one canonical PR per blocker and at most one stacked successor.

If a newer proof supersedes an older PR, preserve/transplant unique evidence first, then mark and close the stale PR.

Exact negative proofs may merge independently when they permanently reduce the candidate/search surface and keep downstream semantic gates fail-closed.

## Merge gate

Before merge:

- re-read fresh `main`;
- ensure the PR does not overwrite newer proof/coordination state;
- run the focused checks required by the changed subsystem;
- require full/native/integration checks where the touched surface requires them;
- keep unsupported semantic gates false;
- change provider count only when a complete external callback boundary is actually removed;
- require `python tools/coordination/render_playable_slice_status.py --strict-human-docs --check` to pass when status-facing docs are touched.

Self-merge is allowed after these gates pass.

## CI policy

Do not add new phase-numbered workflow files.

Add coverage through stable workflow families, pytest/CTest targets or data-driven matrices. Existing historical phase workflows are migration debt and may be removed only after equivalent coverage is proven.

## Authority

PC retail remains the primary semantic authority. Xbox 360 recompilation may be used for navigation/corroboration but cannot replace PC proof.

Known external input identities and hashes are centralized in `coordination/research_inputs.lock.json`. Storage filenames, Drive locations and generated navigation indexes are not semantic authority by themselves.

The v5 single-process coordination files and old phase notes remain historical records and must not be used to select new work.
