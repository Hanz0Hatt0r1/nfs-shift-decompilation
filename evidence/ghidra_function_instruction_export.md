# Targeted Ghidra function instruction export

`tools/ghidra/ShiftFunctionInstructionExporter.java` provides a narrow
instruction-level export for already identified reverse-engineering targets.
It exists to avoid turning the normal evidence database into a multi-million
instruction dump when only a handful of short functions need operand-flow
analysis.

The output format is `SHIFT.GhidraFunctionInstructions/1` JSONL with one row per
requested function.

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
- instruction references with destination and reference type.

The runner invokes `validate_function_instruction_export.py` immediately after
Ghidra. Validation fails if a requested function is unresolved, duplicated,
missing instructions, has malformed byte text, starts at the wrong instruction,
or contains non-increasing instruction addresses.

## Why this is stronger than decompiler parameter types

The current Ghidra export correctly exposes useful physical storage patterns for
the memory wrappers but also propagates questionable semantic types such as
`AptFrameStack *`. The targeted instruction export lets the next analyzer follow
actual `MOV`, `PUSH`, register assignment and `CALL` instructions and determine
which incoming value is forwarded to which backend slot.

The instruction layer should therefore be used to infer argument forwarding;
the decompiler's semantic type labels should remain audit metadata until they
are corroborated independently.

## Evidence boundary

Instruction text and bytes can prove concrete register/stack forwarding and
literal constants. They do not by themselves prove the semantic meaning of an
argument. A forwarded value may become a size/pool/tag/flags candidate only
after its role is independently corroborated by backend behavior, call sites,
diagnostics or runtime evidence.
