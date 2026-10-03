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
The same run also emits:

- `SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1`;
- `SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1`.

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
  memory_free_diagnostic_slice.json
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
`FUN_00638020`, with the known xref at `0x006381b1`. It also places
`Error freeing small alloc (no head) '0x%p' from pool: '%s'` inside
`FUN_00657c30`; existing test evidence records the retail xref as `0x00657cb1`.
The slicers consume the xref inventory dynamically rather than hard-coding those
addresses.

## Allocation diagnostic slice

`analyze_allocation_diagnostic_slice.py` performs a deliberately narrow local
slice around the allocation diagnostic. It requires a straight-line CALL after
the diagnostic xref and reconstructs cdecl-style stack arguments from the
preceding `PUSH` sequence. Simple register copies and standard EBP-frame stack
loads are traced backwards to the physical entry storage of `FUN_00638020`.

For

```text
Unable to allocate %d bytes of memory from the pool (%s)
```

stack argument 0 must be the exact diagnostic format string. Only then is stack
argument 1 interpreted as the `%d` vararg. If that value resolves unambiguously
to one known physical entry storage, the slice may set
`allocation_size_role_proven=true`.

The `%s` vararg is retained as `pool_string_vararg`, but it is **not** promoted
to a pool selector.

## Free diagnostic slice

`analyze_free_diagnostic_slice.py` applies the same fail-closed local model to
`FUN_00657c30` and

```text
Error freeing small alloc (no head) '0x%p' from pool: '%s'
```

The exact diagnostic format must be stack argument 0. Stack argument 1 is then
the `%p` vararg and stack argument 2 the `%s` diagnostic string source. The `%p`
value is traced backwards through simple register copies or standard EBP-frame
loads.

A positive report records only:

```text
free_pointer_role_proven = true
free_pointer_entry_storage = <physical FUN_00657c30 entry storage>
```

This proves the physical input to `FUN_00657c30` that supplies the diagnostic
pointer. It does **not** yet prove which input to `FUN_0064f3a0`, `0064f4c0`,
`FUN_00886930`, or `FUN_00886950` carries that pointer. That requires a separate
inter-function release-chain forwarding join.

The free slice also deliberately does not assign the `%s` diagnostic string to
a pool-selector role and does not interpret `DL` as delete kind or release flag.

## Fail-closed behavior

Both local slicers stop semantic promotion when a branch intervenes between the
diagnostic xref and candidate call, a volatile register crosses an unmodelled
call, a register write is unsupported, the format string is not stack argument
0, or the target vararg does not resolve to a single physical entry storage.

## Remaining boundary

Even positive `%d` and `%p` slices do not prove the complete memory ABI. These
remain separate questions:

- pool-selector semantics;
- alignment semantics;
- release/delete flag semantics;
- release-chain argument provenance;
- compiler `operator new`/`operator delete` identity;
- ownership/lifetime policy.

The next release-side evidence step is therefore inter-function forwarding from
the physical `%p` input of `FUN_00657c30` backwards through
`0064f4c0 -> FUN_0064f3a0` before any wrapper/source argument is named as the
released pointer.
