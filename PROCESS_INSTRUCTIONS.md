# Process coordination instructions

The canonical coordination rules for Process 1, Process 2 and Process 3 are:

[`docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V3.md`](docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V3.md)

Copy/paste prompts for three concurrent workers are maintained in:

[`docs/PLAYABLE_SLICE_PARALLEL_PROCESS_PROMPTS.md`](docs/PLAYABLE_SLICE_PARALLEL_PROCESS_PROMPTS.md)

Every process must read the canonical document before selecting a new substantial task and re-check current `main` whenever a blocker is closed, ownership moves between processes, a cross-process handoff is merged, or the playable-slice graph changes.

The mandatory pre-task question is:

> **Which concrete blocker of the first playable Linux vertical slice does this work remove?**

If proposed work neither shortens the blocker graph nor creates infrastructure immediately required by the next blocker, defer it.

Parallel ownership is strict:

```text
PROCESS 1  retail semantic proof / ABI / provenance / producer / scheduling
PROCESS 2  native physics/runtime consumption of positive handoffs
PROCESS 3  exact resources / scene / Vulkan consumption of live transforms
```

Do not duplicate the same unresolved semantic question in multiple processes. Downstream processes may advance in parallel only by consuming already-positive handoffs, building the immediate fail-closed consumer seam for the next handoff, or fixing a regression on the current playable-slice path.

Individual processes should normally avoid editing the canonical coordination files. The coordinator owns those files so parallel PRs do not conflict on documentation unrelated to their blocker.

Blocker-relevant PRs do not require manual confirmation after every step: they may be merged once focused tests/CI pass, the current `main` has been rechecked, no unsupported semantic gate was promoted, and no newer cross-process handoff is overwritten.
