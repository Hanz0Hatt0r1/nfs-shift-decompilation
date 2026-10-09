# Process 1D — slot3 exact-carrier indirect-call surface

After the merged P1D exact-root/exact-wheel closures, this pass asks a narrow question: do any of those already-proven carrier functions themselves execute a Ghidra-recorded indirect call (`CALLIND`)?

The authoritative Drive SQLite index contains **19,500** `indirect=true` call edges overall, so the edge class is present in the export. The 15 pinned exact-carrier functions are fingerprinted by address, size, and mnemonic SHA-256 before their call rows are inspected.

Result:

```text
whole SQLite indirect-call edges: 19500
proven exact carrier functions:       15
indirect-call edges from carriers:     0
```

The carrier set covers the already-proven direct slot3 lifecycle chains through `FUN_00758b50/FUN_00755950`, `FUN_00770e80` descendants, `FUN_00763570/FUN_00755f80`, `FUN_0076d100` descendants including `FUN_00758810` and `FUN_00769ef0`, and `FUN_00766510/FUN_00758fc0`.

Reproduce:

```bash
python3 tools/ghidra/analyze_p1d_slot3_exact_carrier_indirect_calls.py \
  /path/to/shift_ghidra.sqlite \
  --output out/p1d_slot3_exact_carrier_indirect_call_surface.json
```

## Boundary

This closes only the Ghidra-recorded indirect-call edge surface **with a caller inside the 15 proven carrier functions**. It does not rule out:

- exact pointers stored or escaped for later use;
- callbacks invoked in some other function;
- indirect entry into one of these carriers;
- aliases created outside this set;
- global virtual/indirect dispatch.

The SQLite is navigation/cross-check evidence; object identity continues to come from the merged retail machine contracts. Slot3 writer provenance and P1.3D remain false; provider count remains 7.
