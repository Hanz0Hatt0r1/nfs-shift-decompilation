# Process 1D — 16-carrier direct bulk-opcode closure

This P1.3D slice bounds direct x86 string/bulk-copy instructions inside the complete 16-function exact-root carrier set.

## Machine result

The pinned PC retail 1.02 `SHIFT.exe` is scanned across all 16 complete carrier bodies: 5,178 decoded instructions total.

Direct occurrences of any of the following forms are zero:

- `REP` / `REPE` / `REPNE` prefixed instructions;
- `MOVS*`;
- `STOS*`;
- `LODS*`;
- `SCAS*`;
- `CMPS*`.

Therefore there is no machine-visible aggregate copy through the architectural x86 string-opcode family inside these 16 carrier bodies.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1d_slot3_16carrier_bulk_opcode_pe.py \
  /path/to/SHIFT.exe \
  --output out/p1d_slot3_16carrier_bulk_opcode_closure.json
```

The analyzer verifies the retail executable SHA-256 and the expected instruction count for every carrier before emitting evidence.

## Boundary

This is deliberately not a global aggregate-copy closure. It does not rule out:

- direct calls to `memcpy`/`memmove`-style helpers;
- hand-unrolled scalar copies;
- SIMD copy sequences;
- reconstructed pointers loaded from memory;
- runtime-generated/copied/encoded aliases;
- callback or indirect-entry paths.

Accordingly `aggregate_or_bulk_alias_stores_ruled_out`, `runtime_generated_pointer_stores_ruled_out`, `stored_or_escaped_aliases_ruled_out`, slot3 writer provenance, P1.3D and aggregate P1.3 remain false. External provider count remains 7.

The next P1D step is to inventory direct callees and hand-unrolled copy patterns that can persist a reconstructed selected-wheel alias.
