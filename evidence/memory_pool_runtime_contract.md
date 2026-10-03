# SHIFT memory-pool runtime contract

`src/core/memory_pool_runtime.py` is the shared runtime-facing boundary for the
retail lifetime helpers currently recovered as `FUN_00886900` and
`FUN_00886930`.

The default contract intentionally follows diagnostic-backed helper evidence
without turning that evidence into an unproven compiler ABI. It can consume two
independent higher-level artifacts:

- `SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1` for diagnostic-backed physical roles;
- `SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1` for source argument indices already
  proven by source-to-storage joins.

The source summary cannot promote a runtime role by itself. A source argument
index is admitted only when the corresponding static physical role is also
proven.

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

`build_memory_pool_contract()` with no arguments preserves the historical
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

## Optional source-role evidence

The second optional argument is:

```text
build_memory_pool_contract(retail_static_summary, retail_source_semantic_summary)
```

and requires:

```text
format = SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1
```

For the two runtime helpers, the contract looks only at:

- `FUN_00886900` / `allocation-size`;
- `FUN_00886930` / `released-pointer`.

A source argument index is promoted only when all of the following hold:

1. the matching static physical role is proven;
2. the source summary marks that role proven;
3. the source semantic profiles are globally consistent;
4. the helper has the expected wrapper profile;
5. the role has one stable non-negative `source_argument_index`;
6. at least one proven callsite supports the role;
7. `proven_source_roles` contains the exact role name.

When those conditions are satisfied the contract status becomes:

```text
source-joined-semantic-roles
```

and the corresponding gates become true:

```text
scope.allocation_size_source_argument_index_proven
scope.released_pointer_source_argument_index_proven
```

The exact indices, caller inventory and observed recovered-source expressions
are preserved under `retail_source_semantic_evidence` for audit. If the source
summary is supplied without the matching static proof, the metadata may still be
retained but `proven=false` and no source index is exposed.

A stable source argument index is **not** a proof of the helper's compiler
calling convention or complete ABI. It is only a source-level position joined to
an independently proven physical semantic role through the existing evidence
pipeline.

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

Even with complete static and source semantic summaries the runtime contract
does **not** claim:

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
