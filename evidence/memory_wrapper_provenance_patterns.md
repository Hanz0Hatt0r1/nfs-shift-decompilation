# SHIFT memory-wrapper provenance patterns

`tools/shift_live_dump/summarize_memory_wrapper_argument_patterns.py` summarizes
repeated mappings already present in `SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1`.

The output format is `SHIFT-MEMORY-WRAPPER-PROVENANCE-PATTERNS/1`.

This is a recurrence/stability layer only. It does not assign semantic names to
wrapper inputs or backend parameters.

## Grouping key

Joined backend arguments are grouped by the exact tuple:

```text
(wrapper, backend target, backend physical storage)
```

For example, all observations of `FUN_00886900` forwarding into
`FUN_00638020` `ECX:4` form one pattern, while the same wrapper forwarding into
`FUN_00638020` `EDX:4` is a separate pattern.

## Pattern evidence

Each pattern records:

- occurrence count;
- distinct caller count and caller identities;
- backend target names and observed wrapper call instructions;
- number of occurrences whose source caller -> wrapper edge was independently
  Ghidra-confirmed;
- source-mapped, wrapper-internal and unresolved occurrence counts;
- source argument index histogram;
- raw source argument expression histogram;
- exact integer-literal histogram for mapped source arguments;
- wrapper-internal forwarding-source histogram;
- original forwarding-source histogram.

## Stability classes

`mapping_kind` is derived mechanically:

- `stable-source-argument` — every occurrence is resolved and maps to the same
  source wrapper argument index;
- `stable-wrapper-internal` — every occurrence is resolved and comes from the
  same wrapper-internal forwarding source, such as `constant:0x4`;
- `unresolved` — every occurrence is unresolved;
- `mixed` — observed provenance differs across occurrences or combines resolved
  and unresolved evidence.

`recurrent_pattern=true` requires at least two occurrences.

`crosschecked_stable_pattern=true` requires all of the following:

1. at least two occurrences;
2. every occurrence has a Ghidra-crosschecked source caller -> wrapper join;
3. the mapping is either `stable-source-argument` or
   `stable-wrapper-internal`.

This is intentionally stronger than recurrence alone but remains structural
value-provenance evidence.

## Examples

If two independent source callers use the same wrapper and both instruction
paths show:

```text
source argument 0 -> wrapper Stack[0x4]:4 -> backend ECX:4
```

then that backend storage becomes a recurrent stable source-argument pattern for
index 0.

If every fallback call instead writes a wrapper-created value:

```text
constant:0x4 -> backend EDX:4
```

then that backend storage becomes a recurrent stable wrapper-internal pattern.

Neither result names the value.

## Run

```bash
python3 tools/shift_live_dump/summarize_memory_wrapper_argument_patterns.py \
  out/memory_wrapper_full_evidence/memory_wrapper_argument_join.json \
  --json-out \
  out/memory_wrapper_full_evidence/memory_wrapper_provenance_patterns.json
```

The full memory-wrapper runner produces the same artifact automatically:

```bash
GHIDRA_HOME=/opt/ghidra \
./tools/ghidra/run_memory_wrapper_full_evidence.sh \
  /path/to/SHIFT.exe.c \
  out/shift_ghidra_database \
  /home/pes/ghidra_projects/shift shift SHIFT.exe \
  out/memory_wrapper_full_evidence
```

## Evidence boundary

A recurrent stable pattern proves repeated mechanical provenance only. It does
**not** prove that a source argument or backend storage means:

- allocation byte count / object size;
- alignment;
- pool selector or pool identity;
- allocation tag or flags;
- release/delete kind;
- ownership or reference-counting state;
- compiler `operator new` / `operator delete` identity.

The report therefore keeps semantic-role, allocator-ABI and ownership flags
false. Semantic promotion requires an additional independent layer such as
consistent object-layout evidence, retail diagnostics whose formatting exposes
argument meaning, or runtime behavior that directly distinguishes the candidate
roles.
