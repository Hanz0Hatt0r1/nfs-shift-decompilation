# Process 0 — `CALLOTHER` userop coverage

The full PC retail 1.02 corpus uses Ghidra's x86 language id
`x86:LE:32:default`. Its 283 `CALLOTHER` operations refer to 32 distinct
language-scoped userop indices. All 32 indices resolve to names in the exported
1,632-entry language table; none are outside the table.

The compact report is
[`evidence/pcode_userop_coverage_20261017.json`](../evidence/pcode_userop_coverage_20261017.json).
It is tied to the same compressed corpus SHA-256 and manifest SHA-256 as
[`evidence/full_function_instruction_corpus_20261017.json`](../evidence/full_function_instruction_corpus_20261017.json),
and also records the digest of the language table. The corpus itself remains
outside Git.

The report was generated with the generic
`revenginstr-pcode-userop-coverage` utility from
[`revenginstr`](https://github.com/Hanz0Hatt0r1/revenginstr), using a
read-only Ghidra language-table export. Reproduce it with:

```bash
revenginstr-pcode-userop-coverage \
  /path/to/shift-functions.jsonl.gz \
  /path/to/shift-functions.jsonl.gz.manifest.json \
  /path/to/shift-language-userops.json \
  --output evidence/pcode_userop_coverage_20261017.json
```

This maps indices to names only. It does not define userop behavior or mean
that these operations, or the remaining P-code opcodes, can already be
lowered. Full recompilation remains open.
