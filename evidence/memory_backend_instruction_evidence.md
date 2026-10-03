# SHIFT memory backend instruction evidence

`tools/ghidra/run_memory_backend_evidence.sh` narrows the allocator/release
reverse-engineering step to six retail functions:

- `FUN_00638020` — allocation-diagnostic backend;
- `FUN_006382b0` — create fallback backend;
- `FUN_0064f260` — alternate release branch backend;
- `0x0064f4c0` / `thunk_FUN_0064f3a0` — release thunk;
- `FUN_0064f3a0` — release backend;
- `FUN_00657c30` — function carrying the pool-free diagnostic.

The primary backend output format is `SHIFT-MEMORY-BACKEND-EVIDENCE/1`.
The same run also emits `SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1`.

## Run

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_memory_backend_evidence.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/shift_ghidra_database \
  out/memory_backend_evidence
```

The runner writes:

```text
out/memory_backend_evidence/
  memory_backend_instructions.jsonl
  memory_backend_evidence.json
  memory_allocation_diagnostic_slice.json
```

The full Ghidra export supplies `callgraph.jsonl` and `strings_xrefs.jsonl`; the
six function bodies come from the targeted raw instruction exporter.

## Backend evidence

A positive `SHIFT-MEMORY-BACKEND-EVIDENCE/1` report cross-checks three
independent structures:

1. the requested retail backend instruction bodies were exported;
2. pool allocation/free diagnostic string xrefs land inside those exported
   instruction bodies;
3. the bounded direct release path from the release thunk toward the function
   carrying the pool-free diagnostic exists in the full Ghidra callgraph.

The existing retail evidence places
`Unable to allocate %d bytes of memory from the pool (%s)` inside
`FUN_00638020`, with the known xref at `0x006381b1`. The backend artifact records
whether that exact xref is covered by the targeted instruction body rather than
relying only on the function-level string association.

## Allocation diagnostic slice

`analyze_allocation_diagnostic_slice.py` performs a deliberately narrow local
slice around that exact allocation diagnostic. It requires a straight-line CALL
after the diagnostic xref and reconstructs cdecl-style stack arguments from the
preceding `PUSH` sequence. Simple register copies and standard EBP-frame stack
loads are traced backwards to the physical entry storage of `FUN_00638020`.

For the format string

```text
Unable to allocate %d bytes of memory from the pool (%s)
```

stack argument 0 must be the exact diagnostic format string. Only then is stack
argument 1 interpreted as the `%d` vararg. If that value resolves unambiguously
to one of the known physical entry storages (`ECX:4`, `EDX:4`, or
`Stack[0x4]:4`), the slice may set `allocation_size_role_proven=true` and record
that physical storage in `allocation_size_entry_storage`.

The `%s` vararg is retained as `pool_string_vararg`, but it is **not** promoted
to a pool selector. A string used for diagnostics can be derived from a pool
object/name without being the selector accepted by the allocator itself.

The slice fails closed when a branch intervenes, a volatile register crosses an
unmodelled call, a register write is unsupported, the format string is not stack
argument 0, or the `%d` value does not resolve to one physical entry storage.

## Remaining boundary

Even a positive `%d` slice does not prove the complete allocator ABI. These
remain separate questions:

- pool-selector semantics;
- alignment semantics;
- release/delete flag semantics;
- compiler `operator new`/`operator delete` identity;
- ownership/lifetime policy.

The same evidence discipline applies on the free side: `%p`/`%s` diagnostics
prove participation in a pool-free path, but individual release argument roles
must be traced through the release backend before they are named.
