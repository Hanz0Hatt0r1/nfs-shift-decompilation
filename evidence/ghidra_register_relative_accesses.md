# Ghidra register-relative access inventory

`tools/ghidra/analyze_register_relative_accesses.py` inventories simple x86
register-relative memory operations from targeted instruction exports. Its
output format is `SHIFT.GhidraRegisterRelativeAccesses/1`.

The tool is intended for the next static step around physics/BODY candidates:
find concrete writes such as `[ECX + 0x18]` or reads such as `[ESI + 0xd4]`
without prematurely deciding what ECX/ESI points to or what either displacement
means.

## Required evidence

The analyzer accepts only `SHIFT.GhidraFunctionInstructions/2`. Version 2 adds
Ghidra p-code for every machine instruction. This requirement is fail-closed:
version 1 instruction text is not enough to prove whether an address-like
operand actually performs a memory load/store.

A simple operand is admitted only when both conditions hold:

1. the x86 operand is exactly a general register plus an optional constant
   displacement, for example `[ECX]`, `dword ptr [ECX + 0x18]` or
   `[ESI - 0x4]`;
2. that instruction's Ghidra p-code contains `LOAD`, `STORE`, or both.

The resulting access is classified as `read`, `write`, or `read-write`.

Complex forms such as `[ECX + EDX*4 + 0x10]` are deliberately not simplified.
They are preserved under `unparsed_memory_operands`. A syntactically simple
memory operand whose p-code does not contain a memory LOAD/STORE (for example a
LEA address calculation) is preserved under `pcode_classification_blockers`.

## Run on frontier instructions

```bash
python3 tools/ghidra/analyze_register_relative_accesses.py \
  out/physics_vehicle_frontier_instructions.jsonl \
  --json-out out/physics_vehicle_register_relative_accesses.json
```

Once an independent call-site/ABI proof establishes which register carries a
specific object pointer at a selected boundary, the report can be narrowed
without changing semantics. For example:

```bash
python3 tools/ghidra/analyze_register_relative_accesses.py \
  out/physics_vehicle_frontier_instructions.jsonl \
  --base-register ECX \
  --json-out out/physics_vehicle_ecx_accesses.json \
  --fail-on-blocker
```

`--base-register ECX` means only “show accesses whose syntactic base register is
ECX.” It does **not** mean ECX is automatically `this`, BODY, vehicle or wheel.

## Using the inventory to find state writers

The safe promotion path for a persistent BODY/vehicle state writer is:

1. prove the candidate's callgraph position around an already established
   physics/vehicle boundary;
2. prove the relevant incoming/object pointer provenance at that exact function
   or call site;
3. use p-code to prove the concrete `STORE` instruction and displacement;
4. cross-check the same offset against independent layout/reader/writer or
   constructor evidence;
5. only then assign a semantic field alias when the meaning itself is proven.

Until those conditions are met, the output intentionally remains register +
offset evidence.

## Evidence boundary

This layer does not prove:

- that the base register is an object pointer or `this`;
- BODY/vehicle/wheel/constraint identity;
- pointer aliases across calls;
- field type, size beyond the machine operand, or physical meaning;
- persistence across a frame/update;
- solver ordering or integration semantics.

These unknowns remain explicit blockers rather than inferred names.
