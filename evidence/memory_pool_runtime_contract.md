# SHIFT memory-pool runtime contract

`src/core/memory_pool_runtime.py` is the shared runtime-facing boundary for the
retail lifetime helpers currently recovered as `FUN_00886900` and
`FUN_00886930`.

The module intentionally follows the stronger evidence produced by
`SHIFT-MEMORY-HELPER-SEMANTICS/1` without turning that evidence into an
unproven compiler ABI.

## Proven path evidence

The current retail Ghidra export supports these bounded direct-call paths:

- create-side helper: `FUN_00886900 -> FUN_00638020`;
- `FUN_00638020` references
  `Unable to allocate %d bytes of memory from the pool (%s)`;
- release-side helper:
  `FUN_00886930 -> thunk_FUN_0064f3a0 -> FUN_0064f3a0 -> FUN_00657c30`;
- `FUN_00657c30` references
  `Error freeing small alloc (no head) '0x%p' from pool: '%s'`.

This is sufficient to model the helpers as participants in retail pool
allocation/free paths.

## Runtime use

The contract exports stable helper identities plus small record builders:

- `create_helper_action(...)`;
- `release_helper_action(...)`;
- `release_helper_function(...)`.

These builders preserve the existing runtime JSON shapes. For example,
`release_helper_action(release_old_storage=True)` produces exactly:

```json
{"action": "FUN_00886930", "release_old_storage": true}
```

Camera array growth and camera deleting-wrapper contracts now consume this
shared identity instead of repeating the function literal independently.

## Evidence boundary

The runtime contract does **not** claim:

- `operator new` or `operator delete` identity;
- exact allocator/release calling convention;
- which argument is size, alignment or pool selector;
- ownership/reference-counting policy;
- scalar-delete versus array-delete ABI;
- that every call uses one physical pool implementation.

Those flags remain explicit in `build_memory_pool_contract()["scope"]` so later
reverse-engineering work can promote them independently when direct evidence is
available.
