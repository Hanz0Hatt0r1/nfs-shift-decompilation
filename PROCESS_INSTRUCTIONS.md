# Playable slice coordination instructions

The project uses **three active parallel development processes** for the first playable Linux vertical slice.

Canonical rules:

[`docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md`](docs/PLAYABLE_SLICE_THREE_PROCESS_INSTRUCTIONS_V6.md)

Copy/paste prompts:

[`docs/PLAYABLE_SLICE_THREE_PROCESS_PROMPTS_V6.md`](docs/PLAYABLE_SLICE_THREE_PROCESS_PROMPTS_V6.md)

Machine-readable execution state:

[`evidence/playable_slice_three_process_execution.json`](evidence/playable_slice_three_process_execution.json)

The mandatory pre-task question is:

> **Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

## Active ownership

```text
PROCESS 1
retail proof / ABI / producer / timing
        |
        v
PROCESS 2
native physics / runtime execution
        |
        v
PROCESS 3
resources / scene / renderer / playable bootstrap
        |
        v
native playable Linux vertical slice
```

The processes may advance in parallel on independent queue items. They exchange only explicit fail-closed contracts; unresolved semantic ownership is never transferred merely to keep another process busy.

### Process 1

Owns PC-retail proof, source/value provenance, function ABI/order, remaining collision/contact producer ownership, input/control provenance, Controller #1 timing where required by control execution, and retail camera-follow source/timing.

Current priorities:

```text
P1.1  residual FUN_00766510 frontier:
      a) remaining upstream runtime inputs behind merged Phase748 FUN_00713630 producer
      c) exact FUN_00758fc0 caller scheduling + final transformed-vector add + residual conditional state/diagnostic tail
      CLOSED: later +0x3a28/+0x3a40 direct response block ownership/order
      CLOSED: all four direct FUN_00753650 caller-accumulator sites
P1.2  FUN_00765c40 collision-provider/load-term/residual ownership
P1.3  input -> drivetrain/wheel/control producer chain
P1.4  retail camera-follow source/timing
```

`SHIFT.Fun00766510ResidualOwnershipFrontier/1` is the current P1.1 selection contract. Response config, the earlier `+0x3b20` branch, optional `+0x3bc8/+0x3cxx` branch, later `+0x3a28/+0x3a40` branch, and `SHIFT.Fun00766510DirectCallerAccumulatorSurface/1` are already positive and must not be rediscovered.

### Process 2

Owns native physics/runtime implementation and consumption of positive Process 1 contracts.

Current priorities:

```text
P2.1  COMPLETE — Phase745 same-pass FUN_00766510 session handoff
P2.2  COMPLETE — Phase746 primary caller accumulator delta
P2.3  CURRENT/BLOCKED — preserve Phase747 shared-reference + Phase748 reference-source + Phase749 later-response native work; consume remaining P1.1 and remove complete contact_response; target 7 -> 6 providers
P2.4  consume P1.2 and narrow/remove residual FUN_00765c40
P2.5  replace remaining provider boundaries in dependency order
P2.6  consume proven control chain continuously
```

### Process 3

Owns exact retail resources, Silverstone/BMW scene composition, participant handoff, Vulkan, playable profile/launcher/bootstrap, and final visible integration.

Current priorities remain P3.1–P3.6 as defined by the canonical V6 instructions and machine-readable execution state.

## Shared frontier

Current merged main frontier: **Phase 749**.

Already positive:

```text
BMW BODY0 identity and bind frame
fresh persistent BMW world transform
retail outer cadence
selected-session inner rate = 180 Hz
1/180 s persistent inner execution
normal outer update = six recovered substeps
selected FUN_00765c40 world position/cache/fallback ownership
Phase744 typed CollisionQueryOutput/query scalar handoff
Phase745 selected same-pass FUN_00766510 session handoff
Phase746 primary FUN_00766510 caller accumulator delta
Phase747 shared reference-vector owner/transform
Phase748 FUN_00713630 dynamic reference-source arithmetic/cadence
Phase749 native later +0x3a28/+0x3a40 response-state branch
Phase742 primary FUN_00766510 response application
Phase743 selected BMW application-point owner
Process 1 response-config ownership
Process 1 earlier +0x3b20 branch ownership
Process 1 optional +0x3bc8/+0x3cxx branch ownership
Process 1 later +0x3a28/+0x3a40 branch ownership
Process 1 direct FUN_00753650 caller-accumulator surface (4/4)
```

Active top-level external provider count:

```text
7
```

First architectural reduction target:

```text
FUN_00766510/contact_response removal -> 7 -> 6
```

## Branch and PR protocol

Active branch prefixes:

```text
process-1/<blocker>
process-2/<blocker>
process-3/<blocker>
```

Existing `slice/...` stacked branches may finish normally.

Every blocker-relevant PR uses:

```text
BLOCKER:
INPUT:
OUTPUT:
CONSUMER:
GATES_CHANGED:
LIMITS:
TESTS:
NEXT_OWNER:
NEXT_STEP:
```

Before starting and before merge, re-read current `main`. Self-merge after required tests/CI pass, no conflicts remain, no unsupported semantic gate is promoted, and no newer proof state is overwritten.

## Authority

PC retail remains the primary semantic authority. Xbox 360 recompilation may be used for navigation/corroboration but cannot replace PC proof.

The v5 single-process coordination files remain historical records and must not be used to select new work.
