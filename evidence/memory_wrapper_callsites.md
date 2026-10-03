# SHIFT memory-wrapper source callsites

`tools/shift_live_dump/extract_memory_wrapper_callsites.py` inventories recovered
`SHIFT.exe.c` calls to the five retail memory-wrapper functions around
`0x008868c0..0x00886950`.

The output format is `SHIFT-MEMORY-WRAPPER-CALLSITES/1`.

## Why this layer exists

The Ghidra wrapper-family evidence establishes physical parameter storage and
direct backend calls. The targeted instruction layer can establish how those
physical values are forwarded. Neither layer by itself tells us what expressions
retail callers supplied at each wrapper boundary.

This source-side inventory records that missing part without assigning semantic
parameter names.

For every callsite it stores:

- caller `FUN_...` identity;
- wrapper identity and create/release side;
- the compact recovered source statement;
- assignment target when the wrapper result is assigned to a simple local;
- raw argument expressions in source order;
- observed source arity versus the independently observed physical parameter
  count;
- integer literals contained in each expression and exact simple integer values;
- optional direct caller-to-wrapper confirmation from `callgraph.jsonl`.

Nested calls, casts, array subscripts and quoted commas are kept inside their
argument instead of being split as top-level separators.

## Run

```bash
python3 tools/shift_live_dump/extract_memory_wrapper_callsites.py \
  /path/to/SHIFT.exe.c \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/memory_wrapper_callsites.json
```

`--ghidra-export` is optional. Without it, `ghidra_direct_edge` remains `null`
rather than being guessed.

## Arity mismatches are evidence

The extractor does not repair or discard a recovered call whose source argument
count differs from the physical parameter count recorded by Ghidra. Such a row
gets `arity_matches_physical_parameter_count=false` and remains in the report.

That distinction is useful because a mismatch can indicate decompiler typing or
prototype propagation problems. Silently forcing the call into the expected
shape would destroy exactly the evidence needed to resolve those problems.

## Evidence boundary

A source callsite proves only that the recovered source contains the recorded
call and argument expressions. A matching Ghidra direct edge independently
supports caller/callee identity.

The artifact deliberately keeps all of these false until stronger joins exist:

- `argument_semantic_roles_proven`;
- `allocation_size_role_proven`;
- `pool_selector_role_proven`;
- `alignment_role_proven`;
- `release_flag_role_proven`;
- `allocator_abi_proven`;
- `ownership_semantics_proven`.

In particular, a first argument such as `0xe4` or `count * 4` is not labelled
`size` merely because it looks size-like. Promotion requires agreement between
source callsites, instruction forwarding, pool diagnostics and independently
recovered object/container layouts or runtime behavior.
