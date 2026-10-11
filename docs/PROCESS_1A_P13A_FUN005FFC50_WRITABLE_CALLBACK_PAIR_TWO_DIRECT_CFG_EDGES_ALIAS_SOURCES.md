# Process 1A / P1.3A — callback pair up-to-two-edge CFG alias sources

## Scope

This pass extends `SHIFT.P1A.P13AFun005ffc50WritableCallbackPairDirectCfgAliasSources/1` from one resolved direct CFG edge to at most two. It carries the same exact GPR constant state through direct JMP/Jcc taken successors and conditional fallthrough successors, and checks whether either callback-slot address (`0x00b87b80`, `0x00b87b7c`) is formed or dereferenced through a GPR-based memory operand.

## Retail result

Authority: PC retail 1.02 `SHIFT.exe`, SHA-256 `eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`.

- decoded instructions: 2,847,850
- first-edge successor seeds: 35,329
- second-edge successor seeds: 39,184
- unique exact states at depth 1: 34,890
- unique exact states at depth 2: 36,265
- unique exact states total: 71,155
- maximum straight successor region before a control boundary/state death: 1,224 decoded instructions
- exact callback-slot register formations: 0
- exact GPR-based callback-slot memory operands: 0

## Boundary

This is still a bounded path-depth proof. Three-or-more-edge flows, arbitrary joins/phi reconstruction, stack/heap pointer aliases, nonconstant address construction, external/runtime mutation and reconstructed setter/config entry remain open. An exploratory unbounded exact-state fixed point exceeds 800,000 states before completion, so deeper closure needs relevance pruning or a sound widening strategy rather than silently treating the two-edge result as global.

Only `p13a_fun005ffc50_writable_callback_pair_up_to_two_direct_cfg_edges_computed_alias_source_subset_complete` is promoted. Aggregate alias, writable-memory, callback, slot0/slot1 and P1.3 gates remain fail-closed; external provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_writable_callback_pair_two_direct_cfg_edges_alias_sources.py \
  SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_writable_callback_pair_direct_cfg_alias_sources.json \
  --output evidence/p1a_p13a_fun005ffc50_writable_callback_pair_two_direct_cfg_edges_alias_sources.json
pytest -q tests/test_process1a_p13a_fun005ffc50_writable_callback_pair_two_direct_cfg_edges_alias_sources.py
```

## Next

Add target-relevance pruning/widening for deeper CFG propagation, then classify nonconstant/runtime alias mutation.
