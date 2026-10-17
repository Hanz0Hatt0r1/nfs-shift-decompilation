# Process 0 — portable P-code opcode inventory

The full PC retail 1.02 function corpus has a compact operation inventory in
[`evidence/pcode_instruction_coverage_20261017.json`](../evidence/pcode_instruction_coverage_20261017.json).
It is generated with the generic `revenginstr-pcode-instruction-coverage`
tool from the hash-pinned `REVENGINSTR.GhidraFunctionInstructions/1` corpus.

The report records 41,538 functions, 2,088,152 machine instructions,
9,600,713 P-code operations, and 56 observed opcodes. P-code is emitted for
2,085,683 machine instructions. The remaining 2,469 are 2,460 `NOP` and 9 x87
`WAIT` instructions. `NOP` is a no-op candidate; `WAIT` remains an explicit
translation gap until its semantics are handled or otherwise proven irrelevant.

This report helps define the coverage target for a future portable translator.
It does not establish that any opcode is implemented, that the original C
decompilation is buildable, or that a replacement is linkable or behaviorally
equivalent. Full recompilation remains open.

The 283 `CALLOTHER` operations are separately joined to the exact x86 language
userop table in [`evidence/pcode_userop_coverage_20261017.json`](../evidence/pcode_userop_coverage_20261017.json).
That resolves 32 used indices and leaves 0 indices outside the table; it does
not implement or define their semantics. See
[`PROCESS_0_PCODE_USEROP_COVERAGE.md`](PROCESS_0_PCODE_USEROP_COVERAGE.md).
