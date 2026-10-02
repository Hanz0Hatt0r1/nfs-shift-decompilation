# SHIFT deleting-wrapper evidence

`tools/shift_live_dump/extract_deleting_wrapper_evidence.py` narrows the
lifecycle investigation from teardown-transition candidates to source functions
with a deleting-wrapper-like call shape.

## Required shape

A wrapper candidate must directly call:

1. a teardown-transition candidate already emitted by
   `SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1`; and
2. a configured release helper.

The default release helper is `FUN_00886930`, which existing project evidence
uses for released dynamic-array storage, physics storage and delete-flag object
paths. This extractor deliberately does not re-prove that helper's allocator ABI.

A wrapper is promoted to `deleting_wrapper_shape=true` only when all source
conditions below hold:

- the teardown-transition call is present;
- the release-helper call is present;
- the teardown call appears before the release call in the recovered source
  body;
- the wrapper body contains a narrow bit-0 guard such as
  `(param_2 & 1) != 0` or an equivalent `flags & 1` expression.

When a Ghidra export is provided, both direct call edges are independently
cross-checked and exposed as `ghidra_teardown_edge` and
`ghidra_release_edge`.

## Retail calibration

The current Ghidra call graph already shows the expected paired form for both
concrete path containers:

- `FUN_006cc950` directly calls `FUN_006cc390`, the established
  `AIPolylinePath` teardown-transition function, and then `FUN_00886930`;
- `FUN_006cfed0` directly calls `FUN_006ce660`, the established
  `AISegmentPath` teardown-transition function, and then `FUN_00886930`.

The source-level bit-0 guard is intentionally checked by the new extractor
rather than inferred from callgraph proximity.

## Evidence boundary

`deleting_wrapper_shape` is still not an automatic C++ semantic rename. The
artifact does **not** independently prove:

- compiler-specific deleting-destructor ABI;
- whether the release helper maps exactly to `operator delete`;
- object allocation provenance;
- virtual slot identity;
- array-delete versus scalar-delete semantics.

Those require additional source/disassembly or allocation-site evidence. This
layer only records a conservative wrapper shape that is much more specific than
a generic caller of a teardown function.

## Run

```bash
python3 tools/shift_live_dump/extract_deleting_wrapper_evidence.py \
  /path/to/SHIFT.exe.c \
  --lifecycle out/class_evidence/class_lifecycle_source_evidence.json \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/class_evidence/deleting_wrapper_evidence.json
```

Use repeated `--release-helper FUN_xxxxxxxx` options to replace the default
helper set when investigating another allocator family.

The output format is `SHIFT-CLASS-DELETING-WRAPPER-EVIDENCE/1`.
