# Process 1A / P1.3A — callback pair one-edge CFG alias sources

## Scope

This pass extends `SHIFT.P1A.P13AFun005ffc50WritableCallbackPairComputedAliasSources/1` across exactly one resolved direct control-flow edge. It targets only exact address construction or exact GPR-based memory operands resolving to callback slots `0x00b87b80` and `0x00b87b7c`.

The constant model is unchanged from the upstream straight-line pass: exact 32-bit GPR values produced by MOV immediate/copy, exact LEA, immediate ADD/SUB, and self-XOR zeroing. Calls retain only EBX/ESI/EDI/EBP. Unknown writes kill the affected constant.

## Retail result

Authority: PC retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

- decoded instructions: 2,847,850
- direct CFG successor seeds carrying non-empty exact state: 35,329
- source branch sites: 20,417
- taken direct successors: 20,403
- conditional fallthrough successors: 14,926
- unique `(successor, exact GPR state)` entries: 34,890
- maximum decoded instructions in one successor region before the next control boundary/state death: 1,224
- exact callback-slot register formations after the edge: 0
- exact GPR-based memory operands resolving to either callback slot: 0

The result therefore rules out an exact alias appearing only because a branch-local constant crossed one resolved direct JMP/Jcc edge.

## Boundary

This is deliberately not a multi-edge fixed point. A successor region stops at its next branch/loop/return/trap, and the analysis does not join or iterate states through further CFG edges. Stack/heap aliases, nonconstant address construction, external/runtime mutation and reconstructed setter/config entry remain open.

Only `p13a_fun005ffc50_writable_callback_pair_one_direct_cfg_edge_computed_alias_source_subset_complete` is promoted. Aggregate alias, writable-memory, callback, slot0/slot1 and P1.3 completion gates remain fail-closed; external provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_writable_callback_pair_direct_cfg_alias_sources.py \
  SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_writable_callback_pair_computed_alias_sources.json \
  --output evidence/p1a_p13a_fun005ffc50_writable_callback_pair_direct_cfg_alias_sources.json
pytest -q tests/test_process1a_p13a_fun005ffc50_writable_callback_pair_direct_cfg_alias_sources.py
```

## Next

Replace the one-edge bound with cycle-aware exact-state direct-CFG propagation, then classify nonconstant/runtime alias mutation.
