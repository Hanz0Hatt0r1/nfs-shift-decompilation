# SHIFT memory-wrapper call-site evidence

`tools/shift_live_dump/extract_memory_wrapper_callsites.py` scans recovered
`SHIFT.exe.c` for every direct source call to the established five-function
memory-wrapper family:

- `FUN_008868c0`;
- `FUN_008868d0`;
- `FUN_00886900`;
- `FUN_00886930`;
- `FUN_00886950`.

The output format is `SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1`.

## What is recorded

For every source occurrence the extractor preserves:

- containing `FUN_x` caller;
- wrapper identity and per-caller occurrence number;
- compact source statement;
- raw argument text;
- top-level argument count;
- each raw argument expression;
- every integer literal lexically present in that argument;
- whether the whole argument is exactly one integer literal;
- the exact integer value in that narrow case;
- whether the argument is a simple identifier;
- optional Ghidra confirmation of the direct caller-to-wrapper edge.

The argument splitter respects nested parentheses, brackets, braces and quoted
strings/chars, so an expression such as
`FUN_00112233(param_1, 7)` remains one wrapper argument rather than being split
at its inner comma.

## Aggregates

Each wrapper also gets a compact summary containing:

- call-site and distinct-caller counts;
- observed argument-count histogram;
- literal-bearing argument positions;
- distinct integer literals seen at each position;
- counts of call sites where a position is exactly an integer literal;
- Ghidra-confirmed and Ghidra-rejected call-site counts.

These aggregates are useful for identifying stable patterns before semantic
promotion. For example, a position repeatedly containing `4` is an observation;
it is not automatically named alignment, element size, flags or pool selector.

## Ghidra cross-check

With `--ghidra-export`, the extractor requires `callgraph.jsonl` and checks each
source caller -> wrapper edge against the same structured Ghidra database.
A mismatch is preserved as `ghidra_direct_edge=false`; source evidence is never
silently removed or rewritten to match Ghidra.

Without `--ghidra-export`, the same field remains `null` and the report records
that no independent edge cross-check was requested.

## Run

```bash
python3 tools/shift_live_dump/extract_memory_wrapper_callsites.py \
  /path/to/SHIFT.exe.c \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/memory_wrapper_callsites.json
```

## Evidence boundary

This layer proves source call occurrence, argument expression shape and optional
direct-edge agreement only. It does **not** prove:

- that argument 0 is byte size;
- that any argument is alignment, pool, tag, file/line metadata or flags;
- that release arguments encode delete kind or ownership;
- allocator/free ABI beyond already separate physical forwarding evidence;
- `operator new` / `operator delete` identity;
- ownership/reference-counting policy.

Semantic argument naming must be based on a later join between repeated call-site
patterns, instruction-level forwarding, diagnostics and other independent
evidence.
