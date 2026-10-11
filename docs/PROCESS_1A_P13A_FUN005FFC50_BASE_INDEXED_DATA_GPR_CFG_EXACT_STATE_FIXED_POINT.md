# Process 1A / P1.3A — base/index writable `.data` GPR CFG exact-state fixed point

## Result

The prior four-edge/16-instruction pass showed that arbitrary depth increases keep revisiting a nearly saturated branch surface: 8/32 explores 1,808 states, 16/64 explores 4,827, and 32/128 explores 23,135 while still finding zero indirect transfers. This pass removes those artificial path-length limits and instead deduplicates the exact state `(instruction index, GPR taint/transformed mapping)` independently for each of the 63 verified base/index-addressed writable `.data` seeds.

PC retail 1.02 reaches a finite exact-state fixed point at **1,063 unique GPR states** over **199 direct branch sites**. **78 duplicate cycle/join states** are pruned. The largest seed reaches 83 unique states. There are **0 tainted-register indirect CALL/JMP transfers**.

All terminal states are now semantic rather than budget truncations: 107 all-taint-dead, 67 call stops, and 6 return/trap stops. There are no edge-bound or instruction-window exhaustion states.

## Boundary

This closes `base_indexed_gpr_inter_block_carry_ruled_out=true` only for the exact GPR provenance semantics defined by the existing copy/transform model and resolved direct CFG successors. It does **not** carry stack cells across CFG edges and does not model memory aliases, return-value provenance, unresolved indirect successors, richer semantic phi/value reconstruction, or runtime/heap mutation.

Therefore `base_indexed_inter_block_carry_ruled_out`, `unbounded_multi_edge_or_phi_reconstruction_ruled_out`, aggregate writable/callback/slot0/slot1/P1.3 gates remain false. External provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_base_indexed_data_gpr_cfg_exact_state_fixed_point.py SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_base_indexed_data_four_edge_gpr_carry.json \
  --output evidence/p1a_p13a_fun005ffc50_base_indexed_data_gpr_cfg_exact_state_fixed_point.json
pytest -q tests/test_process1a_p13a_fun005ffc50_base_indexed_data_gpr_cfg_exact_state_fixed_point.py
```

## Next

Carry exact stack cells across CFG edges and compose them with this GPR fixed point. After that, address writable-memory aliases and runtime mutation.
