# Process 1 — lifecycle pointer join

The persistent BODY path is already closed through the solver/post-solve writer,
and the upper vehicle-update side now has a machine-composed pointer-value graph:

```text
receiver callsite
→ local pointer source
→ parent-call register transfer
→ pointer-value closure endpoint
```

The remaining lifecycle blocker is stricter than a vtable hit.  A useful static
join must tie all of the following to the same value source:

```text
unique PE-backed class vtable
→ exact machine instruction referencing that vtable
→ p-code STORE
→ STORE destination base-register origin
→ existing VehiclePointerValueClosure node
```

This block adds:

```text
tools/ghidra/build_vehicle_lifecycle_pointer_join.py
```

Output format:

```text
SHIFT.VehicleLifecyclePointerJoin/1
```

## Inputs

The join consumes four already-existing evidence layers:

1. `SHIFT.VehiclePointerValueClosure/1`;
2. `SHIFT.GhidraVtableXrefInstructionAudit/1`;
3. `SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1`;
4. the original targeted `SHIFT.GhidraFunctionInstructions/2` slice used by the
   vtable audit.

Example:

```bash
python3 tools/ghidra/build_vehicle_lifecycle_pointer_join.py \
  out/vehicle_pointer_value_closure.json \
  out/vtable_xref_instruction_audit.json \
  out/class_evidence/class_lifecycle_source_evidence.json \
  out/vehicle_lifecycle_instructions.jsonl \
  --json-out out/vehicle_lifecycle_pointer_join.json \
  --targets-out out/vehicle_lifecycle_next_targets.txt
```

`--require-verified-join` can be used as a strict gate when a later stage must
not proceed without at least one exact static value-source join.

## Independent raw cross-check

The vtable instruction audit is not trusted blindly.  For every candidate this
stage reopens the raw instruction export and requires:

- the exact function to exist;
- the exact STORE instruction to exist;
- p-code `STORE` on that instruction;
- the exact vtable reference reported by the earlier audit;
- the exact simple memory operand reported by the earlier audit.

Any drift aborts the builder rather than silently reusing stale candidate data.

## STORE-base origin trace

The STORE destination base register is traced backwards only through a very
small linear model:

- `MOV reg, reg` copies;
- `MOV reg, [base + constant]` with p-code `LOAD`;
- `LEA reg, [base + constant]` without p-code `LOAD`;
- an untouched register reaching the beginning of the function.

The trace stops at:

- `CALL` / `CALLIND`;
- branch/conditional-branch/return p-code;
- x86 control-flow instructions;
- unsupported register writers;
- unknown/complex definition sources;
- copy cycles or excessive copy depth.

This is deliberately conservative.  It does not cross a call because caller-
saved/callee-saved conventions alone are not pointer provenance, and it does
not linearize control flow through a branch.

## Exact closure-node requirement

A trace is joined to the vehicle pointer graph only if its terminal source maps
to the exact node ID already present in `SHIFT.VehiclePointerValueClosure/1`.
The currently supported exact source shapes are:

```text
entry:<function>:<register>
memory-source:<function>:<instruction>:<base-register>:<displacement>
```

Examples:

```text
entry:0x00102000:ECX
memory-source:0x00102000:0x00102004:EBX:64
```

Matching a register name in the same function is not enough.  The origin trace
must terminate at the same syntactic source node.

## Class/lifecycle correlation

`SHIFT-CLASS-LIFECYCLE-SOURCE-EVIDENCE/1` supplies the PE-backed unique vtable
identity and source-observed lifecycle candidates.

An exact numeric vtable match may associate the STORE with one class-evidence
row.  The function is then classified, without semantic renaming, as one of:

- `initializer-candidate` — source evidence says the selected initializer writes
  its own unique vtable;
- `teardown-transition-candidate` — source evidence records own-vtable write plus
  an ancestor-vtable-writer call;
- `own-vtable-writer`;
- unclassified.

These are evidence roles, not recovered C++ names.

## What `verified_static_value_source_join` means

A candidate becomes `verified_static_value_source_join=true` only when:

1. the class lifecycle vtable match is unique;
2. the raw STORE/reference/operand cross-check succeeds;
3. the STORE base-register origin trace is `verified`;
4. that terminal source node already exists in the vehicle pointer closure.

This proves a static relationship of the form:

```text
known unique vtable address is stored through a base value
whose proven local source is the same syntactic source represented
in the existing vehicle pointer-value graph
```

It still does **not** prove:

- that offset zero is definitely the final object's vptr field;
- constructor semantics;
- destructor semantics;
- whole-lifetime class identity;
- object ownership;
- vehicle-manager identity;
- scheduler identity;
- input/control ownership;
- persistence of the same object across arbitrary calls or frames.

A non-zero STORE displacement is preserved exactly and is never renamed as a
subobject/vptr offset by guesswork.

## Duplicate or missing class-vtable identity

The join is fail-closed around class identity:

- zero lifecycle rows for a vtable → `unknown`;
- more than one lifecycle row for the same vtable → `ambiguous`;
- exactly one row → numeric class-vtable identity can be `verified`, but only for
  that vtable address and source-evidence row.

No class is chosen by order.

## Next targeted exports

When a vtable maps to a lifecycle row, the report emits lifecycle neighbors as
next instruction targets:

- initializer candidate;
- direct source callers of that initializer;
- teardown-transition candidates.

The current STORE function is omitted from this next-target set because its
instruction slice has already been consumed.

These targets are intended for the next lifetime proof stage: allocation/
initialization transfer, teardown/deallocation transfer, and exact pointer-value
continuity between lifecycle functions and the persistent vehicle-update graph.

## Evidence boundary

The report keeps the following flags false even after a verified join:

```text
vptr_field_proven
constructor_semantics_proven
destructor_semantics_proven
whole_lifetime_class_identity_proven
owner_identity_proven
```

That boundary is intentional.  The stage reduces lifecycle search space and can
prove exact local alias/source relationships without turning callgraph/vtable
adjacency into unsupported class or ownership semantics.
