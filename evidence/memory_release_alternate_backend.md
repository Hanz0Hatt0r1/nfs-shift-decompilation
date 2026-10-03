# Alternate release backend pointer evidence

`tools/ghidra/analyze_release_alternate_backend.py` closes one narrow gap in the
retail release-wrapper family without assigning semantics to the alternate
backend itself.

The existing `SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1` artifact proves that the
`FUN_00886950` wrapper input at `Stack[0x4]:4` is the released pointer by tracing
it through the `0x0064f4c0 -> FUN_0064f3a0 -> FUN_00657c30` path to the exact
pool-free `%p` diagnostic.

Retail forwarding evidence also records a separate `FUN_00886950` branch to
`FUN_0064f260`:

```text
FUN_00886950 Stack[0x8]:4 -> FUN_0064f260 ECX:4
FUN_00886950 Stack[0x4]:4 -> FUN_0064f260 EDX:4
```

The new join does not infer either role from argument position. Instead it
matches the exact already-proven wrapper storage across the two branches. When
that identity is unique and forwarding is confirmed, it emits:

```text
format = SHIFT-MEMORY-RELEASE-ALTERNATE-BACKEND/1
wrapper = FUN_00886950
proven_released_pointer_wrapper_storage = Stack[0x4]:4
alternate_backend = 0x0064f260
alternate_backend_released_pointer_entry_storage = EDX:4
released_pointer_to_alternate_backend_storage_proven = true
```

`ECX:4` is retained under `other_alternate_backend_entry_storage` and receives no
semantic name.

## Fail-closed requirements

The alternate role is promoted only when:

1. the ordinary diagnostic-backed release chain is globally proven;
2. that chain has exactly one proven released-pointer wrapper storage for
   `FUN_00886950`;
3. `FUN_00886950` forwarding is confirmed;
4. at least one transfer to `FUN_0064f260` exists;
5. every matching alternate transfer maps the same proven wrapper storage to
   exactly one backend physical storage;
6. all matching sites agree on that backend storage.

Any missing proof, different source storage, ambiguous match or storage conflict
leaves the result blocked.

## Pipeline

`tools/ghidra/run_memory_wrapper_full_evidence.sh` now emits:

```text
memory_release_alternate_backend.json
```

immediately after `memory_release_pointer_chain.json`. No additional capture or
Ghidra export is required; the normal forwarding artifact already contains the
alternate `FUN_0064f260` site.

The same one-shot runner also supplies this artifact to
`SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1`. When the alternate proof is positive,
the summary publishes:

```text
proven_physical_roles.alternate_release_backend_pointer.proven = true
proven_physical_roles.alternate_release_backend_pointer.function = FUN_0064f260
proven_physical_roles.alternate_release_backend_pointer.entry_storage = EDX:4
proven_physical_roles.alternate_release_backend_pointer.wrapper = FUN_00886950
proven_physical_roles.alternate_release_backend_pointer.wrapper_input_storage = Stack[0x4]:4
```

This extension is optional. Its absence or failure does not change the historical
`static_evidence_chain_complete` result and does not enter the main static
summary blocker list. Extension failures are reported separately under
`alternate_release_backend_evidence.blockers`.

## Scope boundary

A positive artifact proves only a physical role:

> the same value already proven as the released pointer on the retail `%p`
> diagnostic path reaches `FUN_0064f260` in `EDX:4`.

It does **not** prove:

- the overall purpose of `FUN_0064f260`;
- the semantic role of `FUN_0064f260:ECX`;
- why `FUN_00886950` selects this branch;
- pool-selector semantics;
- the role of `DL` elsewhere in the release family;
- delete/destructor kind;
- operator-delete identity;
- ownership or reference-counting policy.
