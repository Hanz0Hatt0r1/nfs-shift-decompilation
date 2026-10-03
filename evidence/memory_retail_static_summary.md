# SHIFT retail static memory evidence summary

`tools/ghidra/run_memory_retail_static_evidence.sh` builds the complete static
memory-wrapper/backend evidence chain without requiring `SHIFT.exe.c` or any
recovered source file.

It needs only:

- the analyzed retail Ghidra project;
- the structured `SHIFT.GhidraEvidenceDatabase/1` export.

## Run

```bash
GHIDRA_HOME=/opt/ghidra \
bash ./tools/ghidra/run_memory_retail_static_evidence.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/shift_ghidra_database \
  out/memory_retail_static_evidence
```

The runner performs the existing targeted wrapper and backend instruction
exports sequentially, then builds:

```text
out/memory_retail_static_evidence/
  forwarding/
    memory_wrapper_instructions.jsonl
    memory_wrapper_forwarding.json
  backend/
    memory_backend_instructions.jsonl
    memory_backend_evidence.json
    memory_allocation_diagnostic_slice.json
    memory_free_diagnostic_slice.json
    memory_release_byte_behavior.json
  memory_release_pointer_chain.json
  memory_retail_static_summary.json
```

## Summary format

`memory_retail_static_summary.json` uses:

```text
SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1
```

It consolidates:

- five-wrapper instruction forwarding status;
- allocation/free diagnostic coverage and release callgraph path;
- allocation `%d` physical entry storage;
- free `%p` physical entry storage;
- released-pointer wrapper input storage traced through the release backend;
- observed behavior of the release-path entry `DL` byte;
- explicit blockers when any stage fails closed.

`static_evidence_chain_complete=true` means all of those static stages were
independently satisfied. `ready_for_source_semantic_join=true` means the proven
allocation-size and released-pointer physical roles can be projected onto source
arguments if a compatible source-callsite artifact is available later.

## Semantic boundary

The summary deliberately leaves these unproven:

- pool selector;
- alignment;
- `DL` as release/delete flag;
- delete/destructor kind;
- compiler `operator new` / `operator delete` identity;
- ownership/lifetime policy.

A complete static evidence chain does not waive those boundaries. It only
consolidates evidence that is already independently proven by raw retail
instructions, diagnostics, and direct callgraph structure.
