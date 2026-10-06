# Playable slice coordination instructions

The project now uses **one active development process** for the first playable Linux vertical slice.

Canonical rules:

[`docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md`](docs/PLAYABLE_SLICE_SINGLE_PROCESS_INSTRUCTIONS_V5.md)

Single-process copy/paste prompt:

[`docs/PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md`](docs/PLAYABLE_SLICE_SINGLE_PROCESS_PROMPT_V5.md)

Machine-readable execution state:

[`evidence/playable_slice_single_process_execution.json`](evidence/playable_slice_single_process_execution.json)

The mandatory pre-task question is:

> **Какой конкретный blocker первого playable Linux vertical slice снимает эта работа?**

If proposed work neither shortens the current blocker nor creates immediately-required reusable infrastructure for that blocker, defer it.

Active execution chain:

```text
static proof / ABI / provenance / scheduling
        -> native physics/runtime
        -> persistent vehicle + fresh world transform
        -> resources / scene / camera / Vulkan
        -> playable Linux slice
```

There are no active Process 1 / Process 2 / Process 3 ownership lanes and no blocker swarm. Positive contracts are internal checkpoints and must be consumed immediately by the same process.

Historical files/contracts containing `Process1`, `Process2`, `Process3`, `process1`, `process2`, or `process3` keep their names for compatibility and evidence traceability only. They do not create active worker ownership or a requirement to wait for another process.

Current shortest blocker after merged PR #1331:

```text
SHIFT.OuterVehicleBMWVHFRootRelation/1       [semantic relation POSITIVE]
        -> materialize selected BMW Vehicle::InitVehicle/FUN_00795d60
           outerVehicle +0x19c/+0x1a0/+0x1a4 values
        -> finite M_outer_to_vhf_root
        -> SHIFT.BMWBody0BindFrameProof/1
        -> persistent fresh BMW world transform
```

Use branch prefix:

```text
slice/<blocker>
```

Every blocker-relevant PR uses:

```text
BLOCKER:
INPUT:
OUTPUT:
CONSUMER:
GATES_CHANGED:
LIMITS:
TESTS:
NEXT_STEP:
```

Before merge, re-read current `main`. Self-merge after required tests/CI pass, no conflicts remain, no unsupported semantic gate is promoted, and no newer proof state is overwritten. After merge, continue with the next shortest blocker.

The former v4 three-process instructions, parallel prompts, and blocker-swarm files are retired historical coordination records and must not be used to select new work.
