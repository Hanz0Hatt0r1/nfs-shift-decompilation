# Process 1: FUN_006880c0 queue provenance

`FUN_006880c0` is a thin wrapper over the generic enqueue primitive, but the PC retail dataflow does **not** give it one fixed queue owner.

## Exact dataflow

The matching PC retail 1.02 source and executable show:

- the only source-visible call to `FUN_006880c0` is inside `FUN_0066bab0`;
- immediately before that call, machine code loads `ECX` from `[ESI+0x8]`, so the queue pointer is `embedded_state+0x8`;
- initializer `FUN_0066bb50` writes its `param_4` directly to that `+0x8` field;
- `FUN_0066bb50` has two source-visible callers, `FUN_0066c980` and `FUN_0066cc00`;
- those are fed by `FUN_0065ff90`, `FUN_0065f970`, and `FUN_0065fa60`, which in turn are reached through API wrappers `FUN_00634ed0`, `FUN_00634f00`, and `FUN_00634f50`.

Therefore the object passed to the generic enqueue path is supplied by an operation-specific producer chain. It is not a fixed global queue that can be classified from `FUN_006880c0` alone.

## Process 1 consequence

This slice intentionally does **not** rule `FUN_006880c0` out as a possible Controller #1 alias yet. Instead, it replaces the vague fixed-owner question with the precise remaining work: classify the operation-object identities that feed the three API wrappers and determine whether any can be the recovered Controller #1 queue.

`FUN_006333f0` remains separately unresolved. Indirect/native APC injection and render/presentation phase locking remain fail-closed.

The Xbox 360 recomp is not required for the promoted dataflow; all claims in this artifact are PC-backed.
