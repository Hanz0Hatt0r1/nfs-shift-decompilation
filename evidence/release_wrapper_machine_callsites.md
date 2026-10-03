# SHIFT release-wrapper machine callsite evidence

This layer measures the physical values supplied by retail callers to
`FUN_00886930` and `FUN_00886950` without using `SHIFT.exe.c` or Ghidra
decompiler parameter types.

Two tools are involved:

- `build_release_wrapper_caller_inventory.py` derives exact direct caller
  functions and call instruction addresses from `callgraph.jsonl`;
- `analyze_release_wrapper_callsites.py` combines those exact sites with targeted
  caller instruction exports and the same fail-closed symbolic x86 engine used
  by wrapper forwarding.

The final format is:

```text
SHIFT-MEMORY-RELEASE-WRAPPER-CALLSITES/1
```

## Run

```bash
GHIDRA_HOME=/opt/ghidra \
bash ./tools/ghidra/run_release_wrapper_callsite_evidence.sh \
  /home/pes/ghidra_projects/shift \
  shift \
  SHIFT.exe \
  out/shift_ghidra_database \
  out/release_wrapper_callsites
```

The caller count is bounded by default to 500 and can be changed with:

```bash
SHIFT_RELEASE_WRAPPER_MAX_CALLERS=250
```

The report explicitly records whether the inventory was truncated.

## Physical storage model

The release wrappers are observed with these entry-storage shapes:

```text
FUN_00886930: ECX:4, DL:1, Stack[0x4]:4
FUN_00886950: ECX:4, DL:1, Stack[0x4]:4, Stack[0x8]:4
```

Caller functions are initialized with generic physical entry storage only:
`ECX`, `EDX/DL`, and bounded entry stack slots. No source-level parameter names
or Ghidra decompiler types are imported.

For each exact direct callsite the report records:

- symbolic source of each wrapper physical argument;
- resolved low-byte constant when `DL` can be reduced to one;
- source assigned to the released-pointer candidate stack slot;
- whether ECX and the first stack pointer slot receive the same symbolic value;
- uncertainty from unsupported instructions or unknown prior calls.

Aggregates include `dl_source_histogram`, `dl_constant_low8_histogram`, and the
ECX/stack pointer duplication fraction.

## Evidence boundary

Even an observed `DL` distribution of only `0` and `1`, or a repeated
ECX/stack pointer duplication pattern, is **not** sufficient to name `DL` as a
release/delete flag. The artifact therefore keeps these false:

```text
release_byte_role_proven
release_flag_role_proven
delete_kind_role_proven
ownership_semantics_proven
```

Semantic promotion requires an independent anchor relating a byte value or bit
to a named release behavior. Unknown calls or unsupported symbolic operations
make affected callsites unresolved rather than guessed.
