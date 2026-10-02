# SHIFT factory create-wrapper evidence

`tools/shift_live_dump/extract_create_wrapper_evidence.py` refines the existing
factory-to-initializer links without assuming that any particular helper is an
allocator.

## Required source shape

For every `SHIFT-FACTORY-INITIALIZER-LINKS/1` row, the extractor walks the
recovered factory body in source call order. For each initializer occurrence it
records the direct call immediately before the initializer and asks whether:

1. that helper call assigns its return value to a local variable; and
2. the same local variable is passed to the initializer call.

When both hold, `source_create_wrapper_shape=true`.

If a Ghidra export is supplied, `create_wrapper_shape=true` additionally
requires independent direct callgraph edges from the factory to both the helper
and the initializer.

The helper call's raw argument expression and integer literal arguments are
preserved. They are evidence for later allocator/size analysis, not automatic
object-size declarations.

## Helper aggregation

Immediate preinitializer helpers are aggregated across all linked classes and
factories. For each helper the report records:

- number of linked classes;
- number of distinct factories;
- number of occurrences where the helper result flows into the initializer;
- class and factory lists.

This allows recurring helper families to emerge from the evidence instead of
being hard-coded. In the current retail callgraph, `FUN_00886900` is a strong
candidate for this investigation because it occurs immediately before both
known path initializers inside `FUN_006d8490`; semantic promotion still depends
on source value-flow and broader allocator evidence.

## Multiple branches

A factory may call the same initializer more than once on separate branches.
The extractor preserves every occurrence and its own immediate predecessor;
it does not collapse them into one guessed allocation path.

Missing factory bodies or missing initializer calls remain explicit through the
`missing` field.

## Evidence boundary

A create-wrapper shape does **not** by itself prove:

- that the preceding helper allocates memory;
- allocator family or ABI;
- object size, even when a literal argument looks size-like;
- placement-new versus heap allocation;
- that the initializer is a C++ constructor;
- ownership or lifetime policy of the returned object.

Those require recurring helper evidence, helper implementation analysis,
allocation/deallocation pairing, or runtime corroboration. The artifact only
proves ordered source calls plus local-value flow into an already established
initializer candidate.

## Run

```bash
python3 tools/shift_live_dump/extract_create_wrapper_evidence.py \
  /path/to/SHIFT.exe.c \
  --initializer-links out/class_evidence/factory_initializer_links.json \
  --ghidra-export out/shift_ghidra_database \
  --json-out out/class_evidence/create_wrapper_evidence.json
```

The output format is `SHIFT-CLASS-CREATE-WRAPPER-EVIDENCE/1`.
