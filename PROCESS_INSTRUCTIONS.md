# Process coordination instructions

The canonical coordination rules for Process 1, Process 2 and Process 3 are:

[`docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V2.md`](docs/PLAYABLE_SLICE_PROCESS_INSTRUCTIONS_V2.md)

Every process must read that document before selecting a new substantial task and re-check it whenever a blocker is closed, ownership moves between processes, or the playable-slice graph changes.

The mandatory pre-task question is:

> **Which concrete blocker of the first playable Linux vertical slice does this work remove?**

If the proposed work neither shortens the blocker graph nor creates infrastructure immediately required by the next blocker, defer it.
