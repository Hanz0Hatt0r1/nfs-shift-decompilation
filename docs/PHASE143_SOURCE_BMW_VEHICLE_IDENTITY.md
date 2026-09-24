# Phase 143 — source-backed BMW vehicle identity

`SHIFT.SourceVehicleIdentityEvidence/1` records the source-level selector in
`SHIFT.exe.c` where vehicle case `2` resolves to the literal `bmw_m3_e36`.

The verifier checks:

- exact SHA-256 of the supplied `SHIFT.exe.c` when invoked on that filename;
- function `FUN_004c32d0` presence;
- exact `case 2 -> pcVar3 = "bmw_m3_e36"` mapping.

The evidence is associated with the existing golden M3 resource namespace but remains
`source-only`: it does not prove that a runtime frame used that selector.

## CLI

```bash
python shift_importer.py source-bmw-vehicle-identity /path/to/SHIFT.exe.c source-bmw-identity.json
```

## Provenance

The current source artifact hash is
`512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9`.
Selector `case 2` is around source line 181347 in the supplied decompilation.