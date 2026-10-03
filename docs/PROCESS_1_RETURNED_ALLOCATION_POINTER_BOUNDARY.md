# Process 1 — returned allocation-pointer semantic boundary

The create-side lifetime chain now reaches a precise machine frontier:

```text
vehicle create wrapper
→ FUN_00886900
→ FUN_00638020 / FUN_006382b0
→ exact inner return-origin target(s)
```

Independent memory evidence also proves a different fact:

```text
FUN_00638020 input storage
→ allocation diagnostic `%d`
→ allocation-size role
→ FUN_00886900 source argument index
```

These facts are both useful, but they answer different questions.

- the return-origin frontier answers **where the returned machine value came from**;
- the memory semantic summaries answer **what selected input arguments mean**.

Neither proves that the returned EAX value is itself an allocated pointer.

This stage publishes that distinction as a stable fail-closed contract.

Tool:

```text
tools/ghidra/build_vehicle_returned_allocation_pointer_boundary.py
```

Output:

```text
SHIFT.VehicleReturnedAllocationPointerBoundary/1
```

## Inputs

```bash
python3 tools/ghidra/build_vehicle_returned_allocation_pointer_boundary.py \
  out/vehicle_create_backend_return_frontier.json \
  out/vehicle_create_backend_return_target_catalog.json \
  out/memory_retail_static_summary.json \
  out/memory_source_semantic_summary.json \
  --json-out out/vehicle_returned_allocation_pointer_boundary.json \
  --targets-out out/vehicle_returned_allocation_pointer_targets.txt
```

The inputs must be:

1. `SHIFT.VehicleCreateBackendReturnOriginFrontier/1`;
2. `SHIFT.VehicleCreateBackendReturnTargetCatalog/1`;
3. `SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1`;
4. `SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1`.

## Machine-return gate

The return-origin frontier must already have:

```text
all_backend_machine_return_origins_resolved = true
```

and the `FUN_00638020` row must have:

```text
machine_return_origins_resolved = true
allocated_pointer_return_proven = false
```

The second condition is intentional.  This stage refuses an upstream artifact
that has silently promoted machine origin into allocator semantics.

The finite inner target set must exactly match the target catalog.  Duplicate,
unsorted or drifting target identity is rejected.

## Static allocation-size facts

The retail static summary can prove:

```text
FUN_00638020
entry storage
→ allocation diagnostic `%d`
→ allocation-size
```

The boundary records:

```text
static_evidence_chain_complete
allocation_size_role_proven
function
entry_storage
semantic_anchor
```

This is a positive physical/semantic fact about an **input value**.

It is not evidence that:

```text
EAX is a pointer
EAX points to newly allocated storage
FUN_00638020 is operator new
allocation request == object size
```

## Source allocation-size facts

`SHIFT-MEMORY-SOURCE-SEMANTIC-SUMMARY/1` can independently prove that the
allocation-size role maps back to a stable source argument of `FUN_00886900`.

The boundary requires the create-helper profile to have:

```text
wrapper = FUN_00886900
allocation_size.source_argument_index_consistent = true
proven_source_roles contains allocation-size
```

This strengthens the create-side **argument** contract only.

A stable source argument index still does not establish the role of the helper's
returned EAX value.

## Exact remaining instruction worklist

The target catalog already filters the backend return-origin targets to exact,
present, non-external functions.

This stage carries those addresses forward as:

```text
required_instruction_targets
```

and `--targets-out` writes them without ranking or substitution.

The resulting file is the remaining instruction-level worklist needed to inspect
what the inner functions actually return.

## Proof requirements

The report publishes five independent requirements:

```text
machine-return-origin
allocation-size-physical-role
allocation-size-source-role
inner-target-instruction-worklist
returned-allocation-pointer-semantic-role
```

The first four may already be satisfied by the current corpus.

The final requirement deliberately remains:

```text
satisfied = false
```

because no existing static/source artifact independently assigns
`allocated-pointer` semantics to the returned EAX value.

The corresponding blocker is:

```text
returned_allocation_pointer_semantic_role_not_proven
```

## Why diagnostics are not enough

`FUN_00638020` references the retail text:

```text
Unable to allocate %d bytes of memory from the pool (%s)
```

That proves the function participates in an allocation-failure/reporting path,
and the existing diagnostic slice can identify the physical input that supplies
`%d`.

It does **not** prove every successful return path returns the allocation result,
nor that the final EAX is the pointer later consumed by the vehicle initializer.
A function may transform, replace, select, wrap or otherwise derive its return
value after an allocation-related operation.

The same rule applies to:

- function names;
- callgraph position;
- recurrence across wrapper families;
- allocation-size arguments;
- failure strings;
- exact machine CALL-result provenance.

Each is useful evidence, but none alone is return-value semantic proof.

## Vehicle context

The exact `vehicle_create_bridges` context is carried forward, including the
persistent vehicle pointer source node and source-backed allocation request.
Each row receives:

```text
returned_allocation_pointer_role_state = unknown
returned_allocation_pointer_role_proven = false
returned_allocation_pointer_required_instruction_targets = [...]
```

This keeps the whole create/lifetime chain joinable while preventing a local
memory observation from being promoted to same-runtime-object identity.

## Evidence boundary

Even when all current positive requirements are satisfied, the report keeps:

```text
returned_allocation_pointer_role_proven = false
allocator_abi_proven = false
operator_new_identity_proven = false
object_size_proven = false
constructor_semantics_proven = false
ownership_semantics_proven = false
same_runtime_object_as_vehicle_update_proven = false
```

The next semantic promotion requires new **static instruction evidence**, not a
new runtime capture: inspect the exact `required_instruction_targets` and prove a
value path from an independently established allocation-producing operation to
the target return EAX on every relevant successful path.

If that proof cannot be established, this boundary remains `unknown` rather than
assigning allocator semantics by convention.
