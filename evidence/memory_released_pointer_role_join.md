# SHIFT released-pointer source role join

`tools/shift_live_dump/join_released_pointer_role.py` promotes a wrapper source
argument to the semantic role `released-pointer` only after the release-side
instruction chain has already been proven.

The output format is:

```text
SHIFT-MEMORY-RELEASED-POINTER-ROLE-JOIN/1
```

## Inputs

The join consumes:

- `SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1`, which maps parsed source arguments to
  physical wrapper entry storage; and
- `SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1`, which traces the pool-free diagnostic
  `%p` value through `FUN_00657c30 <- FUN_0064f3a0 <- 0x0064f4c0` back to
  wrapper input storage.

## Promotion rule

A source callsite receives `released_pointer_role_proven=true` only when:

1. the release-pointer chain is globally proven;
2. that wrapper has exactly one proven pointer-carrying entry storage;
3. the source callsite has `forwarding_join_ready=true`;
4. the proven storage exists in the wrapper's recovered `forwarding_input_storage`;
5. the storage maps positionally to exactly one parsed source expression.

If multiple proven storage candidates exist for one wrapper, the join fails
closed with `conflicting_released_pointer_wrapper_storages`.

## What this proves

A positive row proves that one concrete source expression occupies the exact
wrapper entry storage that was independently instruction-traced to the `%p`
value in the retail pool-free diagnostic.

This is stronger than naming an argument by position or by decompiler type: the
semantic role is inherited from the diagnostic and linked through the recovered
backend/thunk forwarding path.

## Deliberate boundary

The join does **not** promote:

- `DL` to a release/delete flag;
- delete/destructor kind;
- pool-selector semantics;
- `operator delete` identity;
- ownership/lifetime policy;
- the alternate `FUN_00886950 -> FUN_0064f260` branch.

Those remain separate evidence questions.

`tools/ghidra/run_memory_wrapper_full_evidence.sh` emits the joined artifact as:

```text
memory_released_pointer_role_join.json
```
