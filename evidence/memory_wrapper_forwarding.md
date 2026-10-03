# SHIFT memory wrapper instruction forwarding

`tools/ghidra/analyze_memory_wrapper_forwarding.py` is the instruction-level
follow-up to `SHIFT-MEMORY-WRAPPER-FAMILY/1`.

It consumes:

1. `memory_wrapper_family.json`;
2. a targeted `SHIFT.GhidraFunctionInstructions/1` JSONL export;
3. the original Ghidra evidence database for physical function parameter
   storage.

The output format is `SHIFT-MEMORY-WRAPPER-FORWARDING/1`.

## Purpose

The earlier wrapper-family layer proves regular calling-convention and storage
shapes but intentionally does not say what any parameter means. This analyzer
moves one level lower: it follows concrete x86 register/stack movement to show
which wrapper input or literal reaches each backend physical parameter slot.

For example, a straight-line sequence equivalent to:

```text
MOV  ECX,[ESP+4]
MOV  EDX,[ESP+8]
PUSH [ESP+0xc]
CALL backend_fastcall
```

can prove the mapping:

```text
wrapper input 1 -> backend ECX
wrapper input 2 -> backend EDX
wrapper input 3 -> backend Stack[0x4]
```

without calling those inputs `size`, `pool`, `tag`, or anything else.

## Modeled x86 subset

The symbolic state currently handles only explicit, auditable forms needed by
small wrappers:

- `MOV`, `MOVZX`, `MOVSX`;
- `PUSH`, `POP`;
- `LEA` for simple stack addresses;
- `ADD`/`SUB` with immediate values, including `ESP` adjustment;
- zeroing `XOR reg,reg`;
- `LEAVE` and common non-mutating instructions;
- direct `CALL` targets from the instruction export.

Entry stack parameters are tracked relative to the original `ESP`, and the
standard `PUSH EBP; MOV EBP,ESP` frame shape is handled explicitly. Backend
stack cleanup follows the observed Ghidra calling convention for
`__stdcall`/`__fastcall`/`__thiscall`.

## Fail-closed rules

A wrapper cannot become `exact_forwarding_candidate=true` when any of these are
present:

- a required backend call is missing;
- a backend physical parameter resolves to an unknown symbolic source;
- a control-flow branch appears in the modeled instruction sequence;
- an instruction that may mutate state is not modeled;
- wrapper or backend function metadata is missing.

Partial bindings are still preserved so one unknown instruction does not erase
valid observations.

## Semantic type boundary

Decompiler/Ghidra types attached to parameters are copied into the output only
as `reported_type`. They do not influence the symbolic mapping. The source of a
backend argument is represented as an input index, literal constant, return
value, stack address, explicit transform, or unknown value.

## Run

After exporting the five current retail memory wrappers:

```bash
python3 tools/ghidra/analyze_memory_wrapper_forwarding.py \
  out/class_evidence/memory_wrapper_family.json \
  out/memory_wrapper_instructions.jsonl \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/memory_wrapper_forwarding.json
```

## What remains unproven

Even an exact forwarding row proves only the physical movement of values. It
does not prove:

- which create-side input is allocation size or alignment;
- whether another input selects a pool, tag, debug site, or policy;
- whether the extra release-wrapper input is a flag, size, or metadata;
- compiler `operator new` / `operator delete` identity;
- ownership or reference-counting semantics.

Those roles require independent backend/call-site/runtime corroboration.
