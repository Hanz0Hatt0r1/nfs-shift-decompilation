# SHIFT memory backend instruction evidence

`tools/ghidra/run_memory_backend_evidence.sh` narrows the next allocator/release
reverse-engineering step to six retail functions:

- `FUN_00638020` — allocation-diagnostic backend;
- `FUN_006382b0` — create fallback backend;
- `FUN_0064f260` — alternate release branch backend;
- `0x0064f4c0` / `thunk_FUN_0064f3a0` — release thunk;
- `FUN_0064f3a0` — release backend;
- `FUN_00657c30` — function carrying the pool-free diagnostic.

The output format is `SHIFT-MEMORY-BACKEND-EVIDENCE/1`.

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
```

The full Ghidra export directory is used only for `callgraph.jsonl` and
`strings_xrefs.jsonl`; the six function bodies come from the targeted raw
instruction exporter.

## What this proves

A positive report cross-checks three independent structures:

1. the requested retail backend instruction bodies were exported;
2. pool allocation/free diagnostic string xrefs land inside those exported
   instruction bodies;
3. the bounded direct release path from the release thunk toward the function
   carrying the pool-free diagnostic exists in the full Ghidra callgraph.

The existing retail evidence already places
`Unable to allocate %d bytes of memory from the pool (%s)` inside
`FUN_00638020`, with the known xref at `0x006381b1`. The new artifact records
whether that exact xref is covered by the targeted instruction body rather than
relying only on the function-level string association.

## Deliberate boundary

This stage **does not** infer that a particular backend physical argument is the
`%d` byte count, `%s` pool selector/name, `%p` released pointer, alignment, or a
release/delete flag. Those role promotions require a further instruction-level
slice from backend entry storage to the diagnostic-call argument preparation.

Accordingly the report keeps these fields false:

- `allocation_size_role_proven`;
- `pool_selector_role_proven`;
- `alignment_role_proven`;
- `release_flag_role_proven`;
- `allocator_abi_proven`;
- `ownership_semantics_proven`.

That boundary is intentional: diagnostic text proves subsystem participation,
while the targeted backend instructions are the next evidence needed to prove
individual argument roles.
