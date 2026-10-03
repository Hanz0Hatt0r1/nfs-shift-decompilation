# SHIFT memory release-pointer chain

`tools/ghidra/analyze_release_pointer_chain.py` connects the independently
proven pool-free diagnostic `%p` input back to the retail release wrappers.

The report format is:

```text
SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1
```

## Evidence chain

The analyzer requires three existing artifacts:

1. `memory_backend_instructions.jsonl` from the targeted backend export;
2. `memory_free_diagnostic_slice.json`, where
   `SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1` identifies the physical
   `FUN_00657c30` entry storage that supplies the `%p` diagnostic vararg;
3. `memory_wrapper_forwarding.json`, where retail instruction forwarding proves
   how `FUN_00886930` / `FUN_00886950` feed the `0x0064f4c0` release thunk.

The inter-function path is intentionally narrow:

```text
release wrapper
  -> 0x0064f4c0 / thunk_FUN_0064f3a0
  -> FUN_0064f3a0
  -> FUN_00657c30
  -> pool-free diagnostic %p
```

For each hop, the analyzer traces the physical callee storage backwards to one
physical caller entry storage using a small fail-closed x86 subset. Standard
EBP-frame stack inputs and simple register copies are supported. Volatile values
crossing unmodelled calls, unsupported writes, unresolved stack transfer across
tail jumps, or multiple conflicting entry storages block promotion.

## What a positive result proves

A positive `release_pointer_to_wrapper_storage_proven=true` result means the
value printed as `%p` by the retail pool-free diagnostic is instruction-traced
through the release backend and thunk to one or more specific wrapper input
storages.

For wrapper paths the report records:

- wrapper identity/address;
- transfer instruction and `call`/`tail-call` kind;
- physical thunk storage carrying the pointer;
- wrapper input source/storage supplying that value.

Only the path through `0x0064f4c0` is eligible for this proof. The alternate
`FUN_00886950 -> FUN_0064f260` branch is not promoted merely because it may
carry the same wrapper input; it requires its own independent semantic path.

## Deliberate boundary

This artifact does **not** prove:

- that `DL` is a release/delete flag;
- delete kind or destructor policy;
- pool-selector semantics;
- compiler `operator delete` identity;
- ownership or lifetime policy;
- equivalence of the alternate `FUN_0064f260` branch.

Those remain separate evidence questions. The report keeps the corresponding
scope flags false even when released-pointer provenance is proven.

## Full pipeline

`tools/ghidra/run_memory_wrapper_full_evidence.sh` now emits:

```text
memory_release_pointer_chain.json
```

alongside source callsites, wrapper forwarding, source-to-backend argument
provenance, backend diagnostic evidence, and the allocation-size semantic join.
