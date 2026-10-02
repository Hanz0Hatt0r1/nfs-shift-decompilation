# SHIFT recurring lifetime helper-family evidence

`tools/ghidra/build_lifetime_helper_families.py` aggregates unambiguous helper
pairs from `SHIFT-CLASS-LIFETIME-PAIR-EVIDENCE/1`.

The output format is `SHIFT-CLASS-LIFETIME-HELPER-FAMILIES/1`.

## Family key

A family is keyed by the exact pair:

- immediate preinitializer helper from the strong create-side source shape; and
- guarded release helper from the strong delete-side source shape.

Only classes which already have `paired_lifetime_shape=true` and an unambiguous
helper on both sides enter a family. Classes with multiple possible helpers are
kept separately in `ambiguous_classes` rather than assigned to a guessed family.

A pair becomes `recurrent_helper_pair=true` only after appearing in at least two
independent recovered class descriptors.

## Ghidra cross-check

With `--ghidra-export`, each helper is resolved back into `functions.jsonl` and
its immediate direct callees are copied from `callgraph.jsonl`. The report keeps:

- function address/name;
- recovered signature and calling convention;
- recovered parameter metadata;
- mnemonic SHA-256 fingerprint;
- immediate outgoing direct calls.

`crosschecked_recurrent_helper_family_candidate=true` requires:

- recurrence across at least two classes;
- every contributing class already has a Ghidra-paired lifetime shape; and
- both helper functions exist in the same Ghidra export.

This makes the recurring retail pair around helpers such as `FUN_00886900` and
`FUN_00886930` directly inspectable while keeping the semantic conclusion open.

## Preserved arguments

All integer-literal argument sets observed on the create-side helper are
aggregated. Their positions and values are discovery evidence only. In
particular, this layer does not decide that any literal is an allocation size,
alignment, pool selector or count.

## Evidence boundary

Recurrence plus Ghidra function identity does **not** prove:

- allocator or `operator new` identity;
- release helper or `operator delete` ABI;
- a shared heap/arena;
- object-size semantics of helper arguments;
- ownership policy;
- constructor/destructor compiler ABI.

It identifies a repeated class-lifetime helper family worth deeper helper-body
and call-site analysis.

## Run

```bash
python3 tools/ghidra/build_lifetime_helper_families.py \
  out/class_evidence/class_lifetime_pair_evidence.json \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/class_evidence/lifetime_helper_families.json
```
