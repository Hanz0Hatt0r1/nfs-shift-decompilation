# SHIFT memory wrapper family evidence

`tools/ghidra/build_memory_wrapper_family.py` records the robust ABI shape of the
small retail wrapper cluster around the diagnostic-backed pool helpers.

The output format is `SHIFT-MEMORY-WRAPPER-FAMILY/1`.

## Retail cluster

The current Ghidra export places these five small functions next to each other:

| function | observed convention | physical parameter storage | direct backend shape |
| --- | --- | --- | --- |
| `FUN_008868c0` | `__cdecl` | `Stack[0x4]:4` | `FUN_006382b0` |
| `FUN_008868d0` | `__cdecl` | `Stack[0x4]:4`, `Stack[0x8]:4` | `FUN_00638020`, `FUN_006382b0` |
| `FUN_00886900` | `__cdecl` | `Stack[0x4]:4`, `Stack[0x8]:4`, `Stack[0xc]:4` | `FUN_00638020`, `FUN_006382b0` |
| `FUN_00886930` | `__fastcall` | `ECX:4`, `DL:1`, `Stack[0x4]:4` | `thunk_FUN_0064f3a0` |
| `FUN_00886950` | `__fastcall` | `ECX:4`, `DL:1`, `Stack[0x4]:4`, `Stack[0x8]:4` | `FUN_0064f260`, `thunk_FUN_0064f3a0` |

The create-side shape grows from one to three stack parameters while preserving
the previous storage prefix. The release-side shape similarly grows by one stack
parameter while retaining the `ECX` + `DL` fastcall prefix.

`FUN_00886900` and `FUN_00886930` are also the create/release anchors already
joined to the exact retail pool diagnostics by `SHIFT-MEMORY-HELPER-SEMANTICS/1`.

## What is trusted

The builder uses only:

- exact function addresses/boundaries from `functions.jsonl`;
- Ghidra calling-convention labels;
- physical parameter storage (`ECX`, `DL`, stack offsets);
- direct callgraph edges;
- the already independent diagnostic-backed anchor pair.

All expected ABI/backend checks are fail-closed. A missing function, convention
mismatch, storage mismatch, or missing backend edge prevents wrapper-family
promotion while preserving whatever partial evidence remains valid.

## Auto-types are deliberately not semantic evidence

The export currently gives some parameters types such as `AptFrameStack *`.
Those types are retained in `reported_parameter_types` for audit but are never
used by the promotion logic. Replacing every reported type with arbitrary bogus
types leaves the ABI-shape result unchanged in the regression tests.

This matters because recovered decompiler types can be contaminated by unrelated
uses or propagated guesses even when register/stack storage is correct.

## Evidence boundary

A positive `memory_wrapper_family_candidate` means:

- all five expected wrapper functions have the observed convention/storage
  shapes;
- all required direct backend calls are present;
- the create and release parameter-storage progressions are regular;
- the `FUN_00886900` / `FUN_00886930` anchor pair is independently backed by the
  retail pool allocation/free diagnostics.

It still does **not** prove:

- which argument is size, alignment, pool, tag, file/line metadata, or flags;
- the meaning of the additional `FUN_00886950` argument;
- return-value meaning for every create-side wrapper;
- compiler `operator new` / `operator delete` identity;
- allocation ownership or reference-counting rules.

Those require instruction-level argument-forwarding evidence rather than Ghidra
auto-types.

## Run

```bash
python3 tools/ghidra/build_memory_wrapper_family.py \
  out/class_evidence/memory_helper_semantics.json \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/class_evidence/memory_wrapper_family.json
```

## Next evidence stage: physical argument forwarding

After the wrapper family is confirmed, export only the five short function bodies
with `run_shift_function_instructions.sh` and pass that JSONL to
`analyze_memory_wrapper_forwarding.py`. The resulting
`SHIFT-MEMORY-WRAPPER-FORWARDING/1` artifact tracks entry storage and constants
to each known backend call through explicit x86 data flow.

That next layer can prove a mapping such as `Stack[0x4]:4 -> ECX:4` or a constant
written into `EDX:4`; it still does not attach semantic names such as `size`,
`alignment`, `pool` or `delete kind` without independent evidence.
