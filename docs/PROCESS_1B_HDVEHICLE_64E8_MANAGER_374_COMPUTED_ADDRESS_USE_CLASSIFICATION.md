# Process 1B: computed `+0x374` use classification

## Result

The 22-site explicit computed-address inventory is partitioned by what happens to the materialized pointer before its identity is adjudicated.

- 2 sites are `Unwind@...` metadata and are not runtime writers.
- 1 code site (`0x009857b7`) is read-only: the computed region is only compared/read while iterating eight entries and is neither stored through, forwarded nor returned.
- 1 code site (`0x00985bd3`) directly writes through the computed pointer and is therefore the highest-priority receiver-provenance candidate.
- 1 code site (`0x0052902b`) returns the computed pointer and therefore requires consumer-surface analysis.
- 17 code sites forward the computed pointer to callees and require either receiver rejection or callee write semantics before they can be closed.

This reduces the 22 raw materializers to 19 runtime paths where a write can still occur, but it does not identify any of those bases as Participants Manager. Numeric `+0x374` equality is not identity evidence.

The next shortest proof is `0x00985bd3` / `FUN_00985bc0`, because it is the only direct write-through materializer. The final `0x004b86cf` candidate remains fail-closed until all computed-address manager+0x374 paths are bounded.
