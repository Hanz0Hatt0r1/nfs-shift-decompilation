# Process 1A / P1.3A — callback-pair exact aliases through four direct CFG edges

## Purpose

Extend the exact callback-slot address provenance from the two-edge contract without promoting an unbounded/fixed-point claim.

Authority remains PC retail 1.02 `SHIFT.exe` SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

Upstream contract: `SHIFT.P1A.P13AFun005ffc50WritableCallbackPairTwoDirectCfgEdgesAliasSources/1`.

## Model

The analyzer reuses the exact branch-local GPR constant semantics from the preceding callback-slot alias passes and carries non-empty exact state through at most four resolved direct `JMP`/`Jcc` successor edges. State identity is instruction index + exact incoming GPR constants + edge depth. Calls retain only callee-saved `EBX/ESI/EDI/EBP`; unknown writes kill affected constants.

Targets are the writable callback slots `0x00b87b80` and `0x00b87b7c`. The pass records both exact register formations equal to either target and bracketed GPR-based memory operands that resolve exactly to either target.

## Retail result

- decoded instructions: 2,847,850
- successor seeds by depth: 35,329 / 39,184 / 47,455 / 58,362
- unique exact states by depth: 34,890 / 36,265 / 42,307 / 50,536
- total unique exact states: 163,998
- maximum straight successor region: 1,224 decoded instructions
- exact callback-slot register formations: 0
- exact GPR-based callback-slot memory operands: 0

Synthetic regression tests include a positive fourth-edge formation and memory use, and prove that a three-edge bound does not incorrectly claim the fourth-edge case.

## Adjudication

Only `p13a_fun005ffc50_writable_callback_pair_up_to_four_direct_cfg_edges_computed_alias_source_subset_complete` becomes true. No exact callback-slot alias was found in this bounded surface.

The general multi-edge/fixed-point gate remains false. Nonconstant aliases, stack/heap pointer aliases, runtime mutation, indirect writers, aggregate writable-memory closure, callback closure, slot0/slot1 completion and aggregate P1.3 completion remain fail-closed. External provider count remains 7.

## Next

Use target-relevance pruning or sound widening before attempting a deeper exact-state fixed point, then classify remaining nonconstant/runtime callback-slot alias mutation.
