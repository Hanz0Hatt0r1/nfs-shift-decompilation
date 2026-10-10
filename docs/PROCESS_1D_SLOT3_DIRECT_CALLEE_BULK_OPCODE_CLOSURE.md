# Process 1D — direct-callee bulk-opcode closure

This P1.3D slice extends the direct 16-carrier bulk-opcode check one call layer deeper.

## Machine result

Across the 16 exact-root carrier bodies there are:

- 214 immediate direct callsites;
- 82 unique immediate direct callees;
- 9,159 decoded instructions across those 82 callee bodies;
- 0 occurrences of `REP`/`REPE`/`REPNE` or `MOVS*`/`STOS*`/`LODS*`/`SCAS*`/`CMPS*`.

The direct-callsite manifest and direct-callee manifest are SHA-256 pinned. Function sizes come from the pinned Ghidra SQLite export, while opcode adjudication comes from retail machine bytes.

Two non-immediate callsites remain explicit:

- `0x00770ec4` — `call DWORD PTR ds:0xaa60b4`;
- `0x00770f41` — `call DWORD PTR ds:0xaa60b4`.

No runtime target identity is inferred for those sites here.

## Reproduce

```bash
python3 tools/ghidra/analyze_p1d_slot3_direct_callee_bulk_opcode_pe.py \
  /path/to/SHIFT.exe \
  /path/to/shift_ghidra.sqlite \
  --output out/p1d_slot3_direct_callee_bulk_opcode_closure.json
```

The analyzer verifies both pinned input SHA-256 values, the callsite manifest, the 82-callee manifest and the total callee instruction count before emitting evidence.

## Boundary

This closes only x86 architectural string/bulk opcodes in the first immediate direct-callee layer. It does not rule out:

- the two indirect call targets;
- hand-unrolled scalar or SIMD copies;
- deeper callee layers;
- reconstructed pointers loaded from memory;
- callbacks or other indirect-entry paths;
- runtime-generated/copied/encoded aliases.

Therefore `aggregate_or_bulk_alias_stores_ruled_out`, `callee_created_aliases_ruled_out`, `runtime_generated_pointer_stores_ruled_out`, `stored_or_escaped_aliases_ruled_out`, slot3 writer provenance, P1.3D and aggregate P1.3 remain false. External provider count remains 7.
