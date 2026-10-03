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

## Targeted instruction export

When a small set of already identified functions needs argument-forwarding or
literal-level analysis, do not expand the main database into a whole-program
disassembly. Export only those function bodies:

```bash
GHIDRA_HOME=/path/to/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  /path/to/ghidra-projects shift SHIFT.exe \
  out/function_instructions.jsonl \
  FUN_00886900 FUN_00886930
```

`SHIFT.GhidraFunctionInstructions/1` records raw bytes, mnemonic, operand text,
flow destinations and references for every instruction in each requested
function. Use these observations to recover register/stack forwarding. Treat
Ghidra semantic parameter types as provisional unless corroborated separately.

For the established five-function memory-wrapper cluster, use the one-shot
runner instead of typing both stages manually:

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_memory_wrapper_forwarding.sh \
  /home/pes/ghidra_projects/shift shift SHIFT.exe \
  out/memory_wrapper_forwarding
```

It writes both `memory_wrapper_instructions.jsonl` and
`memory_wrapper_forwarding.json`. The latter is
`SHIFT-MEMORY-WRAPPER-FORWARDING/1` and only promotes physical value forwarding;
semantic roles such as size, alignment, pool selector and delete kind stay open
until independently corroborated.

## Important anchors

- `FUN_00854e70` — D3D9 declaration Type conversion;
- `FUN_00859800` — MEB descriptor loader;
- `FUN_00830f80` — declaration canonicalization/creation;
- `FUN_0082e510` — SetVertexDeclaration wrapper;
- provider dispatch/reset paths around `FUN_007b3820`.

A decompiler result establishes a contract boundary, not automatic runtime execution proof.
