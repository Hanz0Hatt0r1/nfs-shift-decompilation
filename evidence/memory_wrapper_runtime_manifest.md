# SHIFT memory wrapper runtime manifest

`tools/shift_live_dump/build_memory_wrapper_runtime_manifest.py` produces a
runtime-facing parameter manifest for the recovered five-function retail memory
wrapper family.

The output format is:

```text
SHIFT-MEMORY-WRAPPER-RUNTIME-MANIFEST/1
```

It consumes:

- `SHIFT-MEMORY-WRAPPER-FORWARDING/1`;
- `SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1`;
- `SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1`.

The builder calls the canonical `src/core/memory_pool_runtime.py` evidence gate
rather than reimplementing the semantic promotion rules.

## Parameter naming policy

Every wrapper starts with its recovered `input_storage` sequence and default
parameter names:

```text
arg0, arg1, arg2, ...
```

A parameter receives a semantic name only when the runtime contract has already
accepted the matching source role and the wrapper's instruction-level forwarding
is confirmed.

Currently the only permitted semantic names are:

- `allocation_size` for the proven `allocation-size` role of
  `FUN_00886900`;
- `released_pointer` for the proven `released-pointer` role of
  `FUN_00886930`.

If the source index is outside the recovered storage shape, the role is not
applied and the manifest records an explicit blocker. Likewise, a wrapper with
unconfirmed forwarding never receives a semantic parameter name even if a
higher-level summary contains a role claim.

## What the manifest does not prove

The manifest deliberately does not convert audit metadata into ABI semantics.
In particular it does not prove:

- the complete calling convention of a helper;
- pool selector or alignment parameter roles;
- `DL` as a release/delete flag;
- delete/destructor kind;
- compiler `operator new` / `operator delete` identity;
- ownership or reference-counting policy;
- object size as distinct from the diagnostic-backed allocation byte count.

Unknown parameters remain `argN`; recognizable constants or repeated callsite
shapes are not enough to rename them.

## Full evidence pipeline

`tools/ghidra/run_memory_wrapper_full_evidence.sh` now emits:

```text
memory_wrapper_runtime_manifest.json
```

alongside the lower-level forwarding, diagnostic, source-role and summary
artifacts. The manifest is a consumer-facing view; those lower-level artifacts
remain the primary evidence.
