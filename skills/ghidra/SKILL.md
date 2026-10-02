---
name: ghidra
description: >-
  Evidence-driven Ghidra workflow for Need for Speed: SHIFT.
---
# Ghidra workflow for SHIFT

## Workflow

1. Record exact binary/decompiler snapshot identity and architecture.
2. Extract callers, callees, vtable slots and data references.
3. Preserve ambiguous table contents when initializer bytes are absent.
4. Emit compact source/address evidence with provenance.
5. Keep static and runtime evidence separate.
6. Join layers only through explicit identity fields.

## Headless evidence database

For an already analyzed Ghidra project, prefer the structured exporter when a
subsystem needs repository-wide cross references or raw program-database data:

```bash
GHIDRA_HOME=/path/to/ghidra \
  ./tools/ghidra/run_shift_export.sh \
  /path/to/ghidra-projects shift SHIFT.exe out/shift_ghidra_database
```

The bundle contains direct function/call/string/global/static-data evidence plus
explicitly marked heuristic candidates for vtables, constructors, computed
switches and factories. Keep `binary.json` and `manifest.json` with the bundle.
Do not promote candidate records to recovered contracts without corroborating
disassembly, PE bytes, call-site or runtime evidence.

## Important anchors

- `FUN_00854e70` — D3D9 declaration Type conversion;
- `FUN_00859800` — MEB descriptor loader;
- `FUN_00830f80` — declaration canonicalization/creation;
- `FUN_0082e510` — SetVertexDeclaration wrapper;
- provider dispatch/reset paths around `FUN_007b3820`.

A decompiler result establishes a contract boundary, not automatic runtime execution proof.
