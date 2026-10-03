# SHIFT memory-wrapper argument provenance

`tools/ghidra/join_memory_wrapper_argument_provenance.py` joins two already
separate evidence layers:

- `SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1` — concrete source calls and raw
  wrapper argument expressions;
- `SHIFT-MEMORY-WRAPPER-FORWARDING/1` — instruction-level symbolic forwarding
  from wrapper entry storage into physical backend parameter storage.

The output format is `SHIFT-MEMORY-WRAPPER-ARGUMENT-PROVENANCE/1`.

## Mechanical substitution

For each wrapper, `input_storage` establishes the positional relationship between
source wrapper arguments and physical wrapper entry storage. A symbolic backend
source such as:

```text
input:Stack[0x4]:4
```

can therefore be projected for a concrete source call such as:

```text
FUN_00886900(0x38, pool_id, flags)
```

into:

```text
source_arg[0](0x38)
```

Derived expressions preserve their operation. For example:

```text
low8(input:DL:1)
```

becomes:

```text
low8(source_arg[1](mode))
```

Wrapper-internal values such as `constant:0x4` or a prior call return remain
wrapper-internal symbolic expressions instead of being incorrectly attributed to
a source argument.

## Partial evidence

The join is deliberately fail-closed without discarding useful partial results.
If source argument count does not match the forwarding layer's `input_storage`,
known positions are still projected, missing input storage is listed explicitly,
and the call site receives `projection_complete=false`.

Likewise, a wrapper whose instruction forwarding is not confirmed can still be
inspected but can never receive a complete provenance projection.

## Run

After producing call-site evidence and the targeted Ghidra forwarding report:

```bash
python3 tools/ghidra/join_memory_wrapper_argument_provenance.py \
  out/class_evidence/memory_wrapper_callsites.json \
  out/memory_wrapper_forwarding/memory_wrapper_forwarding.json \
  --json-out out/memory_wrapper_argument_provenance.json
```

Each output row preserves:

- source caller, wrapper, occurrence and statement;
- original source arguments;
- wrapper physical input-storage mapping;
- every modeled backend call;
- backend physical parameter storage;
- original symbolic forwarding source;
- source argument indices involved in that symbolic source;
- projected concrete source expression;
- unresolved input-storage reasons when projection cannot be completed.

## Evidence boundary

A complete projection proves mechanical provenance from a concrete decompiled
source wrapper argument expression to the physical parameter storage of a known
backend call, through the separately recovered wrapper instruction flow.

It still does **not** prove semantic names such as:

- byte size;
- alignment;
- pool selector;
- allocation tag or flags;
- delete kind;
- ownership state;
- compiler `operator new` / `operator delete` identity.

Those names require independent semantic evidence. This join only makes the
source-to-backend value path explicit and auditable.
