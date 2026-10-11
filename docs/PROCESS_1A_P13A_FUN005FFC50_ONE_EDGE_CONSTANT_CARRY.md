# Process 1A / P1.3A — one-edge constant carry into `FUN_005ffc50`

## Scope

The same-block reconstruction contract intentionally discarded exact register constants at every branch. This pass carries those constants across exactly one direct conditional or unconditional CFG edge and scans the complete immediate successor basic block until the next control transfer.

Calls clear all state. The pass does not attempt return-value provenance, memory aliases, phi merges, indirect branch successors or paths requiring two or more edges.

## Retail result

Across **2,847,850** decoded instructions:

- **17,745** direct branch/jump boundaries have at least one exact GPR constant at the edge;
- **30,181** target/fallthrough successor basic-block paths are evaluated;
- **159,630** successor instructions are simulated;
- the largest immediate successor block contains **225** decoded instructions;
- exact `0x005ffc50` materializations after one edge: **0**;
- indirect `call/jmp reg` to `0x005ffc50` after one edge: **0**.

Synthetic regressions cover both taken-target and fallthrough paths and prove that target reconstruction followed by an indirect transfer is detected.

## Gate effect

Promoted only `p13a_fun005ffc50_one_direct_cfg_edge_constant_carry_subset_complete=true`.

Multi-edge/phi reconstruction, return values, writable/runtime callback slots, encoded/runtime-generated pointers, global callback/incoming-indirect, slot0, slot1, stored aliases and aggregate P1.3 remain fail-closed. Provider count remains 7.

## Next step

Trace multi-edge/phi, return-value and writable-memory/runtime provenance to `FUN_005ffc50`. Same-block and one-direct-edge exact constant construction no longer need to be rescanned.
