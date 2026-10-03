# SHIFT diagnostic-backed memory helper semantics

`tools/ghidra/build_memory_helper_semantics.py` strengthens recurring lifetime
helper-family evidence with direct retail diagnostics from the Ghidra export.

The output format is `SHIFT-MEMORY-HELPER-SEMANTICS/1`.

## Retail diagnostics

The current retail export contains two high-value memory-pool diagnostics:

- `FUN_00638020` references `Unable to allocate %d bytes of memory from the pool (%s)`;
- `FUN_00657c30` references `Error freeing small alloc (no head) '0x%p' from pool: '%s'`.

The known recurring create helper `FUN_00886900` directly calls
`FUN_00638020`. The known release helper `FUN_00886930` reaches the free
 diagnostic through the direct-call chain
`FUN_00886930 -> thunk_FUN_0064f3a0 -> FUN_0064f3a0 -> FUN_00657c30`.

Those relationships are not hard-coded as function identities by the analyzer.
It discovers diagnostic functions from `strings_xrefs.jsonl` and finds bounded
paths through direct edges in `callgraph.jsonl`.

## Path proof

For each lifetime helper family the analyzer performs separate bounded searches:

- create helper -> function referencing the retail pool-allocation diagnostic;
- release helper -> function referencing the retail pool-free diagnostic.

Every positive result stores the complete function path, the individual
callgraph edges, path depth, string address/value and xrefs.

A family is marked `diagnostic_backed_pool_lifetime_family=true` only when both
paths exist inside the configured depth/node limits. A depth-limited miss stays
a miss; the other side may remain independently positive.

The default maximum call depth is 4 and the per-search node budget is 5000.
Both are explicit CLI parameters.

## Evidence boundary

This layer is strong enough to say that a helper participates in a concrete
retail pool-allocation or pool-free path. It still does **not** prove:

- compiler `operator new` / `operator delete` identity;
- exact allocator ABI;
- argument meanings such as size, alignment or pool selector;
- scalar-delete versus array-delete ABI;
- ownership or reference counting policy;
- whether every call through the helper uses the same backing pool.

The distinction matters because the release path passes through a larger memory
management subsystem rather than a single symmetric leaf primitive.

## Run

```bash
python3 tools/ghidra/build_memory_helper_semantics.py \
  out/class_evidence/lifetime_helper_families.json \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/class_evidence/memory_helper_semantics.json
```

Use `--max-depth` and `--max-nodes` to tighten bounded traversal when auditing a
large or noisy helper family.
