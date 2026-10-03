# Process 1 — lifecycle pointer join

The persistent BODY path is already closed through the solver/post-solve writer,
and the upper vehicle-update side now has a machine-composed pointer-value graph.
Process 1 also has an independent local alias proof:

```text
exact literal candidate-table STORE
→ stable base-register value across the local interval
→ receiver-source memory use
```

That proof is `SHIFT.VehicleVtablePointerAlias/1`. This block does not duplicate
its register-continuity analysis. Instead it asks whether that already-verified
local value relationship can be joined to both the persistent vehicle pointer
graph and independent PE/source-backed class lifecycle evidence.

Tool:

```text
tools/ghidra/build_vehicle_lifecycle_pointer_join.py
```

Output:

```text
SHIFT.VehicleLifecyclePointerJoin/1
```

## Inputs

The builder consumes exactly three existing contracts:

1. `SHIFT.VehiclePointerValueClosure/1`;
2. `SHIFT.VehicleVtablePointerAlias/1`;
3. `SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1`.

Example:

```bash
python3 tools/ghidra/build_vehicle_lifecycle_pointer_join.py \
  out/vehicle_pointer_value_closure.json \
  out/vehicle_vtable_pointer_alias.json \
  out/class_evidence/class_lifecycle_source_evidence.json \
  --json-out out/vehicle_lifecycle_pointer_join.json \
  --targets-out out/vehicle_lifecycle_next_targets.txt
```

`--require-verified-join` is a strict optional gate for consumers which require
at least one fully joined static candidate.

## Imported local alias proof

`SHIFT.VehicleVtablePointerAlias/1` already requires an exact shape equivalent
to:

```text
MOV [base + displacement], literal_table_address
```

with p-code `STORE`, the literal equal to the same-instruction referenced
candidate table address, and the same local base-register value preserved across
the interval to the receiver-source memory use.

Calls, branches, returns, partial-register writes, implicit GPR writes and
unsupported interval instructions prevent that contract from becoming
`verified`.

This lifecycle join therefore does not re-run a weaker local tracer. It imports
that result and fails closed if an alias marked `verified` no longer contains:

- a verified exact literal table STORE;
- exact stored-address/reference equality;
- destination-base/receiver-source-base equality.

## Exact pointer-closure node

For each alias candidate the builder reconstructs the exact receiver-source node
identifier used by `SHIFT.VehiclePointerValueClosure/1`:

```text
memory-source:<function>:<instruction>:<base-register>:<displacement>
```

Example:

```text
memory-source:0x00715700:0x00715730:ESI:64
```

The join proceeds only if this exact node already exists in the pointer closure.
A repeated register name, equal displacement in another function, nearby call or
similar address is not accepted as identity evidence.

Thus the pointer side of a verified join is:

```text
exact literal table STORE
→ verified local same-pointer alias
→ exact receiver-source memory node
→ existing persistent vehicle pointer-value graph node
```

## PE/source-backed class correlation

`SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1` independently supplies class rows with
PE-backed unique vtable addresses and source-observed lifecycle candidates.

The stored table address from the alias report is matched numerically to
`own_vtable`:

- no matching lifecycle row → `unknown`;
- more than one matching row → `ambiguous`;
- exactly one row → class-vtable address correlation is `verified`.

No row is selected by file order or class name similarity.

The matching function receives only the lifecycle role already supported by the
source evidence:

- `initializer-candidate` when the selected initializer literally writes its own
  unique vtable;
- `teardown-transition-candidate` when the source evidence records the own-vtable
  write plus ancestor-vtable-writer transition;
- `own-vtable-writer` for another literal writer;
- unclassified otherwise.

These role labels remain evidence categories. They are not automatic C++
constructor/destructor names.

## Verified lifecycle-pointer join

`verified_lifecycle_pointer_join=true` requires all of the following:

1. `same_pointer_table_store_state == verified` from the independent alias
   contract;
2. its exact receiver-source node exists in
   `SHIFT.VehiclePointerValueClosure/1`;
3. the exact stored table address maps to exactly one lifecycle class row.

The resulting statement is deliberately narrow:

```text
a specific candidate-table address is stored through a locally proven pointer
value, that same receiver-source value is already represented in the persistent
vehicle pointer graph, and the numeric table address is the unique PE-backed
vtable recorded for one lifecycle-evidence class row
```

This materially narrows class/lifetime work without claiming more than the
static evidence supports.

## Offset zero

The imported alias may report:

```text
same_pointer_offset_zero_table_store_verified = true
```

This is stronger layout evidence than a heuristic vtable xref, but even in a
verified lifecycle-pointer join it does not prove that the field is a C++ vptr.
Non-zero offsets are preserved exactly and are not renamed as subobject vptrs.

## Next targeted exports

For a unique lifecycle match, the builder emits the remaining lifetime neighbors:

- initializer candidate;
- direct source callers of the initializer;
- teardown-transition candidates.

The current table-STORE function is omitted when it is already the analyzed
function.

These targets are the next lifetime-transfer frontier. The next block should
prove value continuity across initialization/allocation and teardown/deallocation
calls, preferably by composing existing class lifetime/deleting-wrapper evidence
rather than inventing class semantics from callgraph adjacency.

## Fail-closed conditions

The builder aborts on contract-format drift and on internally inconsistent
`verified` alias rows, including a verified alias whose exact STORE is no longer
verified or whose destination base no longer matches the receiver-source base.

It emits blockers rather than guesses when:

- local alias proof is ambiguous or unknown;
- the exact receiver-source node is absent from the pointer closure;
- the stored table address is absent from lifecycle evidence;
- multiple lifecycle rows claim the same numeric vtable address.

## Evidence boundary

Even a verified join leaves all of these false:

```text
vptr_semantics_proven
constructor_semantics_proven
destructor_semantics_proven
whole_lifetime_class_identity_proven
owner_identity_proven
input_control_provenance_proven
scheduler_identity_proven
```

The point of this stage is to close an exact static correlation boundary while
preserving the distinction between value provenance, layout evidence, lifecycle
candidates and final semantic identity.
