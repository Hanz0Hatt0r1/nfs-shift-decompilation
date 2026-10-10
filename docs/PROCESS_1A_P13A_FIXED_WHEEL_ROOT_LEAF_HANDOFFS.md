# Process 1A / P1.3A — fixed four-wheel leaf handoffs

This contract closes two additional exact wheel-root receiver families on the machine-proven global vehicle `0x00c13700`.

## `FUN_007582f0 -> FUN_00756010`

The caller at `0x0074d8b1` loads `ECX=0x00c13700` and calls `FUN_007582f0` at `0x0074d8b6`. The callee preserves the vehicle in EAX and materializes all four roots:

- `+0x400` -> call `FUN_00756010`;
- `+0xe80` -> call `FUN_00756010`;
- `+0x1900` -> call `FUN_00756010`;
- `+0x2380` -> tail jump `FUN_00756010`.

`FUN_00756010` is a complete 43-byte leaf. It performs only scalar floating-point field updates relative to the wheel receiver and neither stores/copies/pushes nor further forwards the receiver value.

## `FUN_0076ed60 -> FUN_00753020`

The setup caller at `0x0074dfe3` loads `ECX=0x00c13700` and calls `FUN_0076ed60` at `0x0074dfe8`; the prologue pins `ESI=ECX` at `0x0076ed64`. The window `0x0076ee3c..0x0076ee84` materializes the same four roots and calls `FUN_00753020` once for each.

`FUN_00753020` is a complete 192-byte leaf. It copies scalar configuration fields from its source argument into fields relative to the wheel receiver. It contains no call/jump and no store, push, or GPR copy of the receiver pointer itself.

## Gate effect

The contract records eight positive transient wheel-root handoffs but zero persistent root escapes in the two complete leaf callees.

Promoted only:

- `p13a_fixed_four_wheel_leaf_handoff_subset_complete = true`.

Still fail-closed:

- reconstructed wheel pointers;
- runtime-generated selected-wheel pointer stores;
- stored/escaped aliases;
- callbacks/indirect entry;
- slot0, slot1 and aggregate P1.3.

Provider count remains 7.

The next materializer is `FUN_007653f9 -> FUN_00760d70`, whose callee enters a non-contiguous/trampolined body and needs a separate control-flow proof. `FUN_00757318` remains the next dynamic indexed-root lifetime after that.
