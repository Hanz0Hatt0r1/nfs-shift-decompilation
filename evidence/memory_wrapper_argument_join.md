# SHIFT memory-wrapper argument provenance join

`tools/shift_live_dump/join_memory_wrapper_argument_evidence.py` joins the two
independent memory-wrapper evidence layers already recovered for retail SHIFT:

- `SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1` — recovered source caller and raw
  argument expressions;
- `SHIFT-MEMORY-WRAPPER-FORWARDING/1` — instruction-level value forwarding from
  wrapper entry storage to known backend calls.

The output format is `SHIFT-MEMORY-WRAPPER-ARGUMENT-JOIN/1`.

## What a positive join proves

For a source call such as a wrapper invocation with arguments `A, B, C`, the
forwarding artifact independently defines the wrapper entry storage, for example:

```text
Stack[0x4]:4
Stack[0x8]:4
Stack[0xc]:4
```

The instruction-level analyzer may then show a backend argument source such as:

```text
input:Stack[0x4]:4
```

When the source call was parsed completely and its argument count exactly matches
the forwarding input-storage count, the join may mechanically record:

```text
source argument 0 (A)
  -> wrapper Stack[0x4]:4
  -> backend ECX:4
```

This is value provenance. It is stronger than comparing parameter positions by
eye because both halves of the mapping are explicit evidence artifacts.

## Fail-closed rules

Positional source mapping is disabled when any of these conditions holds:

- source arguments were not parsed completely;
- source argument count differs from the independently recovered wrapper
  input-storage count;
- the wrapper's instruction forwarding is not confirmed;
- the forwarding expression is unresolved or depends on more than one wrapper
  input storage.

The row remains in the report with its blocker instead of being repaired or
silently dropped.

A direct source caller -> wrapper Ghidra edge is tracked separately. A row gets
`ghidra_crosschecked_join=true` only when the mechanical source/forwarding join
is ready and the caller edge is independently confirmed.

## Wrapper-internal values

A backend argument can originate entirely inside the wrapper. For example a
forwarding source such as:

```text
constant:0x4
```

contains no caller input storage. Such a value is recorded as
`wrapper_internal_source=true`; it is never incorrectly attributed to one of the
source call's arguments.

## Run

```bash
python3 tools/shift_live_dump/join_memory_wrapper_argument_evidence.py \
  out/memory_wrapper_callsites.json \
  --forwarding out/memory_wrapper_forwarding/memory_wrapper_forwarding.json \
  --json-out out/memory_wrapper_argument_join.json
```

The source callsite artifact and forwarding artifact may be produced separately;
this tool only joins their explicit records and does not require the Ghidra
project itself.

## Evidence boundary

A join-ready row proves only the mechanical path:

```text
recovered source expression
  -> wrapper entry storage
  -> modeled backend argument storage
```

It still does **not** prove that any position means:

- byte count / allocation size;
- alignment;
- pool selector or pool identity;
- allocation tag or flags;
- release/delete kind;
- ownership or reference-counting state.

The report therefore keeps `argument_semantic_roles_proven`,
`allocation_size_role_proven`, `pool_selector_role_proven`,
`alignment_role_proven`, `release_flag_role_proven`, `allocator_abi_proven` and
`ownership_semantics_proven` false.

Semantic promotion requires another independent layer, such as agreement with
retail allocation/free diagnostics plus a recovered object/container layout or
runtime behavior.
