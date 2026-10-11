# Process 1A / P1.3A — base/index writable `.data` four-edge GPR carry

## Result

Starting from the 63 verified base/index-addressed writable `.data` loads, this subset carries GPR provenance path-sensitively across at most **4 direct CFG edges** and at most **16 decoded instructions** after each load. Taken and fallthrough states remain separate; predecessor states are not merged. Calls stop state and indirect successors are never guessed.

PC retail 1.02 explores **1,107 bounded states** across **186 unique direct branch sites**. Edge traversals by depth are 88 at depth 1, 130 at depth 2, 107 at depth 3, and 67 at depth 4. There are **0 tainted-register indirect CALL/JMP transfers**.

Termination inventory: 118 all-taint-dead, 67 call stops, 8 direct-jump stops, 8 return/trap stops, **15 branch stops at the edge bound**, and **19 window-exhausted states**. Because bounded paths actually reach both limits, the aggregate inter-block/phi gate remains open.

## Boundary

Promoted only `p13a_fun005ffc50_base_indexed_data_up_to_four_direct_cfg_edge_gpr_carry_subset_complete=true`. Fifth-plus edges, paths beyond 16 instructions, phi/fixed-point merging, stack state carried across edges, calls/returns, aliases and runtime/heap values remain fail-closed. External provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_base_indexed_data_four_edge_gpr_carry.py SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_base_indexed_data_implicit_push_pop.json \
  --output evidence/p1a_p13a_fun005ffc50_base_indexed_data_four_edge_gpr_carry.json
pytest -q tests/test_process1a_p13a_fun005ffc50_base_indexed_data_four_edge_gpr_carry.py
```

## Next

Classify or extend the 15 fifth-edge and 19 window-exhausted states, then address phi/fixed-point and runtime alias provenance.
