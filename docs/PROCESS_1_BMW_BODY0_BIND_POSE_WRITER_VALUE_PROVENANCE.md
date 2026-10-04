# Process 1 — BMW BODY0 bind pose-writer value provenance frontier

## Playable-slice blocker reduced

The first playable Linux slice still lacks a retail `M_BODY0_bind`, so Process 2
Phase 706 cannot produce the source-backed BMW world transform consumed by
Process 3 Phase 649.

The preceding Process 1 target-role stage proves only which physical
`FUN_007b7840` ABI parameter receives the complete persistent BODY origin/basis
writes.  It intentionally does not prove the values written into those fields.

This stage narrows that remaining value question to exact structured p-code
slices for every admitted pose STORE.

Machine-readable format:

```text
SHIFT.BMWBody0BindPoseWriterValueProvenance/1
```

Tool:

```text
tools/ghidra/analyze_bmw_body0_bind_pose_writer_value_provenance.py
```

No original game execution or new runtime capture is required.

## Inputs

```text
SHIFT.BMWBody0BindPoseWriterTargetRole/1
SHIFT.GhidraFunctionInstructions/2 for exact FUN_007b7840
```

The target-role input must already be positive for exactly one register-backed
`persistent_BODY_pose_record_target` and must still keep BODY0/bind readiness
negative.

The tool revalidates that the target-role STORE witnesses jointly cover every
persistent origin/basis byte.  A truncated or contradictory upstream report is
rejected rather than silently accepted.

## Value input, not address input

A p-code `STORE` has separate address-space, address and value inputs.  For each
admitted origin/basis write this stage starts its dependency frontier at:

```text
STORE input[2]  # written value
```

not at the BODY target pointer.

This matters because the previous target-role proof answers:

```text
where is the value written?
```

while this phase asks:

```text
where did the written value come from?
```

The two proof dimensions remain separate.

## Structured p-code dependency worklist

For every admitted pose STORE the report retains:

- exact machine instruction;
- target BODY displacement and STORE width;
- structured STORE value varnode;
- most recent structured p-code definition when one exists;
- backward dependency slice from that value definition;
- terminal source varnodes;
- dependency opcodes;
- whether the slice contains a memory `LOAD`;
- floating-register roots;
- direct machine CALLs preceding the STORE for audit.

Terminal roots are classified conservatively as:

```text
constant
address-space-selector
general-register
floating-register
other-register
unresolved-unique
external-or-memory-varnode
```

Only constants/address-space selectors are non-blocking by classification alone.
Register and memory identities still require source-backed joins.

## x87/SSE call-return guard

Instruction-level Ghidra p-code does not by itself establish that a preceding
machine `CALL` defines a later `ST0` or `XMMn` value.

Therefore:

```text
CALL helper
...
FSTP [BODY + lane]
```

is recorded as:

```text
floating-register terminal root
+ preceding direct CALL audit rows
```

but never promoted to:

```text
that CALL returned this exact floating value
```

A separate path-aware floating-call-return proof is required.

This preserves the same fail-closed policy already used by the
`FUN_007afdd0` scalar-provenance tooling.

## CFG/SSA boundary

The targeted exporter provides instruction p-code, not whole-function SSA high
p-code.  A linear last-definition graph is useful for producing a finite exact
worklist but is not a proof across control-flow merges.

The report therefore explicitly states:

```text
linear_instruction_pcode_dependency_frontier_only = true
cfg_ssa_value_identity_proven = false
```

Any value crossing branches must be promoted using path-aware machine/register/
stack provenance rather than by treating the dependency slice as a PHI-aware
proof.

## Memory source boundary

When a pose value depends on `LOAD`, the report preserves that dependency but
does not infer whether its address is:

- stack parameter storage;
- another field of the BODY;
- an SDF/builder source object;
- a global/static constant table;
- another runtime object.

Exact object/address semantics are a separate finite worklist.

## Handoff

A structurally complete report can set:

```text
pose_writer_pose_store_value_dependency_frontier_ready = true
BODY0_bind_origin_basis_value_dependency_worklist_ready = true
```

but always leaves:

```text
BODY0_bind_origin_basis_values_ready = false
BODY0_pointer_at_bind_callsite_ready = false
BODY0_bind_frame_proof_ready = false
```

A dependency slice is therefore never confused with concrete bind values.

## Next joins

The nearest static work after this frontier is now explicit:

1. resolve general-register terminal roots through physical ABI/caller
   provenance;
2. resolve memory LOAD addresses to exact stack/object/global sources;
3. resolve floating-register roots across exact x87/SSE producer or helper-call
   boundaries;
4. materialize source-backed origin/basis bind-time values;
5. independently join the proven BODY target parameter at the selected
   initialization callsite to BMW chassis BODY0.

Only after both the target-pointer and value sides are positive may Process 1
construct a finite non-singular D3D row-vector `M_BODY0_bind` and emit a positive
`SHIFT.BMWBody0BindFrameProof/1`.

## Preserved negative claims

This stage does not claim:

- that `FUN_007b7840` is the retail bind initializer;
- that a preceding CALL produced an x87/SSE terminal register;
- CFG-SSA value identity;
- a parameter semantic role from its name/type/ordinal;
- BODY0 callsite identity;
- concrete bind origin/basis values;
- the BODY0 bind matrix;
- Phase 706 commit cadence;
- camera or renderer scheduling.
