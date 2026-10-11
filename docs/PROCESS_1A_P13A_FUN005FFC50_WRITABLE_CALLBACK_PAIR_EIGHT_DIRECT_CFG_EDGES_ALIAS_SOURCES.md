# Process 1A / P1.3A — callback-pair exact aliases through eight direct CFG edges

## Purpose

Double the bounded direct-CFG exact-state horizon after the four-edge negative result, while keeping fixed-point and global alias claims fail-closed.

Authority: PC retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

Upstream: `SHIFT.P1A.P13AFun005ffc50WritableCallbackPairFourDirectCfgEdgesAliasSources/1`.

## Model

The pass carries the established exact GPR constant state through at most eight resolved direct `JMP`/`Jcc` successor edges. The state key retains instruction index, complete exact incoming GPR state and edge depth. Calls preserve only callee-saved `EBX/ESI/EDI/EBP`; unknown/clobbered values are killed rather than guessed.

Targets remain writable callback slots `0x00b87b80` and `0x00b87b7c`.

## Retail result

- decoded instructions: 2,847,850
- successor seeds by depth 1..8: 35,329 / 39,184 / 47,455 / 58,362 / 72,068 / 88,419 / 105,925 / 125,644
- unique exact states by depth 1..8: 34,890 / 36,265 / 42,307 / 50,536 / 60,521 / 72,035 / 83,429 / 97,087
- total unique exact states: 477,070
- maximum straight successor region: 1,224 decoded instructions
- exact callback-slot register formations: 0
- exact GPR-based callback-slot memory operands: 0

## Adjudication

Only `p13a_fun005ffc50_writable_callback_pair_up_to_eight_direct_cfg_edges_computed_alias_source_subset_complete` is promoted. The general multi-edge/fixed-point gate remains false. Nonconstant aliases, stack/heap aliases, runtime mutation, indirect writers, writable-memory closure, callback closure, slot0/slot1 and aggregate P1.3 remain fail-closed. External provider count remains 7.

## Boundary and next step

State growth is still substantial and a depth bound is not a fixed point. The next useful step is target-relevance pruning or a sound may-state widening that explicitly reports unresolved `TOP` flows instead of treating them as negative evidence.
