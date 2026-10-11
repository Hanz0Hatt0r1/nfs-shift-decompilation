# Process 1A / P1.3A — base/index GPR+stack CFG exact-state fixed point

This pass composes the GPR fixed point from #1949 with exact modeled stack state across resolved direct CFG edges for the same 63 base/index-addressed writable `.data` seeds.

On PC retail 1.02 `SHIFT.exe` (`eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1`) the joint state key is instruction index + exact GPR taint/transformed mapping + exact EBP/ESP `mov` stack cells + implicit push/pop taint stack. Calls stop carried state after transfer checks; indirect successors are never guessed.

## Result

The finite fixed point contains **1,106** exact GPR+stack states, **80** duplicate cycle/join states pruned, **201** direct branch sites, and at most **83** states for one seed. Eight unique branch-successor carries have live stack taint; at most three tracked stack cells are live at once.

Across the fixed point there are 2 unique exact stack spills, 1 exact stack reload, 35 unique tainted pushes and 0 tainted pop reloads. The new reload is the EBP spill chain `0x004da33e -> 0x004da344 [ebp-0x28] -> 0x004da362 edx`, which survives the branch at `0x004da34e`. No tainted-register indirect `CALL/JMP` is reached.

Semantic terminations are 104 all-taint-dead, 70 call-stop and 7 return/trap.

## Adjudication

`p13a_fun005ffc50_base_indexed_data_gpr_stack_cfg_exact_state_fixed_point_subset_complete`, `base_indexed_stack_state_across_cfg_edges_ruled_out`, and the composed exact-state `base_indexed_inter_block_carry_ruled_out` are true. Writable aliases/runtime mutation, arbitrary phi/value reconstruction, callbacks/indirect entry, slot0/slot1 and aggregate P1.3 remain fail-closed. Provider count remains 7.

## Next

Classify writable-memory aliases and runtime mutation now that exact base/index GPR+stack inter-block carry is closed.
