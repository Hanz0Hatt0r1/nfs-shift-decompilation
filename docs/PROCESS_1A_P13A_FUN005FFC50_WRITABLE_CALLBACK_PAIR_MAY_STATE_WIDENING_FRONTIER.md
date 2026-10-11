# Process 1A / P1.3A — callback pair may-state widening frontier

## Why this pass exists

The exact callback-slot CFG series remains negative through twelve direct edges, but path enumeration is no longer an efficient closure strategy: the twelve-edge pass already contains 1,014,242 exact states, and a depth-free exact-state worklist exceeded 1.8 million unique states while still growing.

This pass replaces path enumeration with a finite may-state join for the **same exact-constant source class**. It does not claim global alias closure.

## Abstract state

For each tracked GPR at a CFG entry, retain a union of up to eight candidate exact constants. A ninth distinct value widens that register to `TOP`. `TOP` is never interpreted as negative evidence: any address expression depending on `TOP` is emitted as an unresolved frontier site.

Initial states are the existing branch-local exact constant states. Direct `JMP`/`Jcc` successors are joined until the finite abstract state reaches a fixed point. Calls preserve only the established callee-saved GPR constant state.

## Retail result

PC retail 1.02 `SHIFT.exe` (`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`):

- decoded instructions: 2,847,850
- initial successor seed edges: 35,329
- initial joined successor entries: 32,592
- joined CFG entries: 116,695
- processed entries: 452,675
- entry-state updates: 420,083
- maximum updates for one entry: 35
- `TOP` entry-register instances: 45,681
- `TOP` formation sites: 1,591
- `TOP` memory-use sites: 2,793
- exact callback-slot hits: **0**

The 2,793 `TOP` memory-use sites are therefore the concrete unresolved frontier for this widened exact-constant class.

## Adjudication

Promote only `p13a_fun005ffc50_writable_callback_pair_may_state_widening_frontier_subset_complete=true`.

`writable_callback_pair_may_state_top_frontier_empty=false`, so no multi-edge/global alias, writable-memory, callback, slot0/slot1, or aggregate P1.3 gate is promoted. Provider count remains 7.

## Next step

Classify the 2,793 `TOP` memory-use sites by address expression and producer ancestry. The objective is to separate widened values that cannot address either callback slot from genuinely unresolved callback-slot-relevant flows, instead of increasing the raw CFG edge budget further.
