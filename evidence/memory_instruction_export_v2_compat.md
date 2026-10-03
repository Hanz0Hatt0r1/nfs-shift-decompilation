# Memory instruction-export v2 compatibility

The targeted Ghidra instruction exporter now emits
`SHIFT.GhidraFunctionInstructions/2`, which preserves structured p-code beside
the exact machine instructions.

The older memory-wrapper and memory-backend analyzers were written against
`SHIFT.GhidraFunctionInstructions/1`. Their machine-instruction logic remains
useful, but feeding a v2 row directly into them fails closed on the format
identifier.

## Compatibility boundary

`tools/ghidra/normalize_function_instruction_export.py` creates a separate
version-1 compatibility copy:

- the source v2 JSONL is never rewritten;
- row/function/instruction ordering is preserved;
- machine bytes, mnemonics, operands, flows and references are preserved;
- only the row format is lowered to `/1`;
- per-instruction `pcode` is removed from the compatibility copy.

Unknown instruction-export versions are rejected rather than silently lowered.
A version-1 source can also be normalized, which keeps existing fixtures and
older checked-in evidence usable.

## Runner outputs

`run_memory_wrapper_forwarding.sh` now writes:

```text
memory_wrapper_instructions_v2.jsonl   # primary raw targeted export
memory_wrapper_instructions.jsonl      # v1 compatibility copy
memory_wrapper_forwarding.json
```

`run_memory_backend_evidence.sh` writes:

```text
memory_backend_instructions_v2.jsonl   # primary raw targeted export
memory_backend_instructions.jsonl      # v1 compatibility copy
memory_backend_evidence.json
...
```

The legacy memory analyzers consume only the compatibility files. New p-code
analysis must consume the `_v2.jsonl` files or another direct version-2 export.

## Evidence boundary

The compatibility conversion does not create new evidence. In particular it
does not prove argument semantics, field semantics, allocator ABI, ownership,
BODY/vehicle identity, or persistent state. It exists only to preserve the
machine-instruction analysis pipeline while the newer p-code layer is adopted
incrementally.
