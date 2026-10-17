# Process 0 — P-code memory-space coverage

The full PC retail 1.02 corpus contains 589,262 `LOAD` and 704,175 `STORE`
operations. All 1,293,437 reference language address-space ID `0x1a1`, which
the read-only x86 language export identifies as `ram`. No used IDs remain
unmapped.

The report is
[`evidence/pcode_address_space_coverage_20261017.json`](../evidence/pcode_address_space_coverage_20261017.json).
It records the corpus, manifest, and address-space-table digests and joins
only the exact Ghidra language id `x86:LE:32:default`. The source corpus and
raw language table remain outside Git.

The report was generated with the generic
`revenginstr-pcode-address-space-coverage` tool from
[`revenginstr`](https://github.com/Hanz0Hatt0r1/revenginstr), using a
read-only Ghidra address-space export:

```bash
revenginstr-pcode-address-space-coverage \
  /path/to/shift-functions.jsonl.gz \
  /path/to/shift-functions.jsonl.gz.manifest.json \
  /path/to/shift-language-address-spaces.json \
  --output evidence/pcode_address_space_coverage_20261017.json
```

This resolves the IDs used by P-code memory operations. It does not provide
the guest memory image, implement `LOAD`/`STORE`, or establish runtime parity.
Full recompilation remains open.
