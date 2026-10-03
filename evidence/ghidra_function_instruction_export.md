# Targeted Ghidra function instruction export

`tools/ghidra/ShiftFunctionInstructionExporter.java` provides a narrow
instruction-level export for already identified reverse-engineering targets.
It exists to avoid turning the normal evidence database into a multi-million
instruction dump when only a handful of functions need operand/data-flow
analysis.

The current output format is `SHIFT.GhidraFunctionInstructions/2` JSONL with one
row per requested function. The validator remains backward-compatible with
version 1 exports so earlier checked-in/local evidence can still be audited, but
new register-relative memory analysis requires version 2.

## Memory-wrapper preset

For the current memory-wrapper investigation, export the five neighboring
functions with:

```bash
cd /home/pes/nfs-shift-decompilation

GHIDRA_HOME=/opt/ghidra \
bash tools/ghidra/run_shift_function_instructions.sh \
  <project-dir> <project-name> SHIFT.exe \
  out/memory_wrapper_instructions.jsonl \
  FUN_008868c0 FUN_008868d0 FUN_00886900 FUN_00886930 FUN_00886950
```

Use the real Ghidra project directory/name in place of `<project-dir>` and
`<project-name>`. `bash ...` is intentional so the command also works in a fresh
checkout if the executable bit was not preserved by an archive or sync tool.

The same runner can consume addresses selected by
`build_proven_callgraph_frontier.py`, keeping large physics/vehicle exploration
targeted instead of exporting the whole executable instruction stream.

## Per-instruction fields

Each selected function records:

- exact function entry/name/size/calling convention;
- instruction address;
- raw instruction bytes as lowercase hexadecimal;
- mnemonic;
- Ghidra instruction text;
- each default operand representation separately;
- flow type and fallthrough address;
- explicit flow destinations;
- instruction references with destination and reference type;
- the ordered Ghidra p-code operations generated for that machine instruction.

The runner invokes `validate_function_instruction_export.py` immediately after
Ghidra. Validation fails if a requested function is unresolved, duplicated,
missing instructions, has malformed byte text, starts at the wrong instruction,
contains non-increasing instruction addresses, mixes export versions, or emits a
version-2 instruction without a valid p-code list.

## Why p-code matters for physics/BODY work

Instruction text can show an operand such as `dword ptr [ECX + 0x18]`, but that
string alone is not a sufficient fail-closed memory-access proof. For example,
`LEA EAX,[ECX + 0x18]` computes an address without loading or storing the pointed
memory.

Version 2 therefore preserves Ghidra's low-level p-code next to the exact machine
instruction. Static analyzers can require `LOAD` and/or `STORE` before admitting
a register-relative access, while still retaining the original instruction bytes
and operands for audit.

`tools/ghidra/analyze_register_relative_accesses.py` uses this boundary. It does
not infer that ECX is `this`, BODY, vehicle or wheel; it records only the proven
register + displacement + p-code memory operation.

## Why this is stronger than decompiler parameter types

The Ghidra database can expose useful physical storage patterns while also
propagating questionable semantic types. The targeted instruction export lets a
later analyzer follow actual `MOV`, `PUSH`, register assignment, `CALL`, `LOAD`
and `STORE` evidence rather than trusting a decompiler type label.

The instruction/p-code layer should therefore be used to establish concrete
storage and forwarding facts. Semantic type labels remain audit metadata until
corroborated independently.

## Evidence boundary

Instruction text, bytes and p-code can prove concrete machine operations and
literal/register storage relationships. They do not by themselves prove:

- the semantic meaning of an argument or field;
- object-pointer provenance across calls;
- BODY/vehicle/wheel identity;
- persistence or frame-to-frame state;
- ownership/lifetime semantics;
- physical names such as position, velocity, force or impulse.

Those require separate call-site, layout, constructor/vtable, reader/writer or
other static evidence before promotion.
