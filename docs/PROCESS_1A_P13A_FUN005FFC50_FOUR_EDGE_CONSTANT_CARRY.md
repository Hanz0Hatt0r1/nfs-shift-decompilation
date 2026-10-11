# Process 1A / P1.3A — up-to-four-edge `FUN_005ffc50` constant carry

## Scope

`SHIFT.P1A.P13AFun005ffc50OneEdgeConstantCarry/1` bounded exact GPR constants across one direct CFG edge. This pass extends that same path-sensitive model through **up to four** direct conditional/unconditional edges while keeping taken and fallthrough states separate.

Calls terminate carried state. Indirect branch successors are not guessed. The pass does not merge alternative predecessor states and therefore does not claim an unbounded phi/fixed-point result.

## Retail result

Across **2,847,850** decoded instructions, the upstream scan supplies **17,745** branch seeds and **30,181** first-edge successor paths. The four-edge worklist evaluates:

- depth 1: **29,768** unique state/block evaluations;
- depth 2: **21,280**;
- depth 3: **17,555**;
- depth 4: **16,071**;
- total: **84,674** unique state/block evaluations;
- **443,364** simulated successor instructions.

Within this bounded class:

- exact `0x005ffc50` materializations: **0**;
- indirect `call reg` / `jmp reg` transfers with the tracked register equal to `0x005ffc50`: **0**.

Synthetic tests prove a three-edge reconstruction followed by `call eax` is detected, and that an intervening call terminates carried provenance.

## Gate effect

Promoted only `p13a_fun005ffc50_up_to_four_direct_cfg_edge_constant_carry_subset_complete=true`.

Still fail-closed: five-plus-edge/unbounded phi reasoning, return-value provenance, writable/runtime-memory entry, encoded/reconstructed callback entry globally, dynamic registry registration, callback/incoming-indirect closure, runtime-generated selected-wheel stores, stored aliases, slot0, slot1, and aggregate P1.3. Provider count remains 7.

## Reproduction

```bash
python tools/ghidra/analyze_p1a_fun005ffc50_four_edge_constant_carry.py /path/to/SHIFT.exe \
  --upstream evidence/p1a_p13a_fun005ffc50_one_edge_constant_carry.json \
  --output evidence/p1a_p13a_fun005ffc50_four_edge_constant_carry.json
pytest -q tests/test_process1a_p13a_fun005ffc50_four_edge_constant_carry.py
```

## Next step

Trace five-plus-edge/phi, return-value, and writable/runtime-memory provenance to `FUN_005ffc50`. The direct exact-constant path-sensitive class through four direct CFG edges no longer needs to be rescanned.
