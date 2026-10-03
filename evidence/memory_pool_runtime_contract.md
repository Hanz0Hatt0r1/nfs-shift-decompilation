# SHIFT memory-pool runtime contract

`src/core/memory_pool_runtime.py` is the shared runtime-facing boundary for the
retail lifetime helpers currently recovered as `FUN_00886900` and
`FUN_00886930`.

The default contract intentionally follows diagnostic-backed helper evidence
without turning that evidence into an unproven compiler ABI. It can also consume
the newer `SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1` artifact and admit only the
physical semantic roles independently proven there.

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

## Optional physical-role evidence

`build_memory_pool_contract()` with no argument preserves the historical
boundary and does not promote argument roles.

`build_memory_pool_contract(retail_static_summary)` accepts only a mapping with:

```text
format = SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1
```

The contract can then expose two stronger roles when the summary includes both a
positive proof flag and concrete physical storage:

- `allocation-size`: physical `FUN_00638020` entry storage traced to the retail
  allocation diagnostic `%d`;
- `released-pointer`: wrapper input storage instruction-traced through the
  release backend to the retail pool-free diagnostic `%p`.

A bare `proven=true` without physical storage fails closed and does not promote
the role.

These become:

```text
scope.allocation_size_argument_role_proven
scope.released_pointer_argument_role_proven
```

and are mirrored under `retail_static_evidence` with their exact storage.
Observed `DL` behavior is carried as evidence metadata only.

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

Camera array growth and camera deleting-wrapper contracts consume this shared
identity instead of repeating the function literal independently.

## Evidence boundary

Even with a complete retail static summary the runtime contract does **not**
claim:

- `operator new` or `operator delete` identity;
- complete allocator/release calling convention or ABI;
- pool-selector or alignment semantics;
- `DL` as a release/delete flag;
- delete/destructor kind;
- ownership/reference-counting policy;
- scalar-delete versus array-delete ABI;
- that every call uses one physical pool implementation.

`allocation-size` is also not automatically renamed `object-size`: the allocated
byte count could include headers, padding, arrays, or other wrapper-specific
adjustments. `object_size_argument_proven` therefore remains false until that
stronger relationship is separately demonstrated.
