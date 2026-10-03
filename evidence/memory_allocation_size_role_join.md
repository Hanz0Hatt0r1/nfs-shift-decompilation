# SHIFT allocation-size semantic evidence join

`tools/shift_live_dump/join_allocation_size_role.py` is the first memory-wrapper
stage that may promote a source argument from pure value provenance to a named
semantic role.

The promotion is intentionally narrow. It requires both independent evidence
chains to be positive:

1. `SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1` must prove which physical
   `FUN_00638020` entry storage supplies the `%d` value in
   `Unable to allocate %d bytes of memory from the pool (%s)`;
2. `SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1` must prove that the same physical
   backend storage receives one parsed source argument through wrapper entry
   storage.

The output format is `SHIFT-MEMORY-ALLOCATION-SIZE-ROLE-JOIN/1`.

## Full pipeline

`run_memory_wrapper_full_evidence.sh` now emits:

```text
memory_wrapper_callsites.json
forwarding/memory_wrapper_forwarding.json
memory_wrapper_argument_join.json
memory_wrapper_provenance_patterns.json
backend/memory_backend_evidence.json
backend/memory_allocation_diagnostic_slice.json
memory_allocation_size_role_join.json
```

The semantic join is performed only after both the wrapper provenance and
backend diagnostic slice have been generated.

## Positive row

A row may set:

```text
allocation_size_role_proven = true
allocation_size_source_argument_index = <n>
allocation_size_source_argument_expression = <expression>
```

only when the backend `%d` role is independently proven and the exact physical
backend storage maps to one source argument in a join-ready callsite.

The report retains the full observation used for the promotion: backend call
instruction, backend target, backend storage, forwarding source, source argument
index and source expression.

## Fail-closed cases

No semantic role is assigned when:

- the backend diagnostic slice did not prove `%d` storage;
- the source-to-backend row is not join-ready;
- the proven backend storage is not observed at the allocation backend call;
- the same storage maps to multiple source argument indices;
- mapped source expressions conflict.

## What remains unproven

This promotion proves the `allocation-size` role only for source arguments that
reach the independently identified `%d` storage. It does not prove:

- `%s` is the allocator pool selector;
- alignment semantics;
- complete allocator ABI;
- `operator new` identity;
- ownership or lifetime rules;
- release/delete flag semantics.

Those remain separate evidence problems. The next corresponding release-side
step is to trace the pool-free diagnostic `%p` backwards through
`FUN_00657c30` and the `0064f4c0 -> 0064f3a0` release chain before naming the
released-pointer or flag inputs.
