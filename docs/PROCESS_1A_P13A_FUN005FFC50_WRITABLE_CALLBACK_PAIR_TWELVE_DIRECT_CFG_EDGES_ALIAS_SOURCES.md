# Process 1A / P1.3A — callback pair up-to-twelve-edge CFG alias sources

## Scope

This bounded pass extends the exact callback-slot address propagation model from eight to twelve resolved direct `JMP`/`Jcc` successor edges for PC retail 1.02 `SHIFT.exe` (`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`). Targets remain writable callback slots `0x00b87b80` and `0x00b87b7c`.

The state key is `(instruction index, exact incoming GPR constant state, edge depth)`. Calls preserve only the established x86 callee-saved constant state; unsupported/non-exact values stay absent rather than guessed.

## Retail result

The analyzer decodes 2,847,850 instructions and explores these exact-state depths:

- depth 1: 34,890 unique states
- depth 2: 36,265
- depth 3: 42,307
- depth 4: 50,536
- depth 5: 60,521
- depth 6: 72,035
- depth 7: 83,429
- depth 8: 97,087
- depth 9: 110,979
- depth 10: 126,067
- depth 11: 141,772
- depth 12: 158,354

Total unique exact states: **1,014,242**. Successor seeds at depths 9..12 are 148,181 / 171,180 / 195,549 / 221,237. Maximum straight successor region remains 1,224 decoded instructions.

No exact callback-slot register formation is observed and no GPR-based memory operand resolves to either callback slot.

## Adjudication

Promote only `p13a_fun005ffc50_writable_callback_pair_up_to_twelve_direct_cfg_edges_computed_alias_source_subset_complete=true`.

Do **not** promote `writable_callback_pair_multi_edge_computed_alias_sources_ruled_out`, aggregate alias/writable-memory/callback gates, slot0/slot1 completion, or aggregate P1.3 completion. Provider count remains 7.

## Boundary / next step

This is not a fixed point. The state surface is already above one million states at depth 12, so simply increasing the edge budget is no longer the preferred closure strategy. The next useful step is target-relevance pruning or a sound may-state widening with explicit unresolved/TOP flows, followed by nonconstant/runtime callback-slot mutation classification.
