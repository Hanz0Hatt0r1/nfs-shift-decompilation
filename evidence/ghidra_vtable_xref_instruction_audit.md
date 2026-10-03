# Ghidra exact vtable-xref instruction audit

`tools/ghidra/analyze_vtable_xref_instructions.py` narrows the construction
frontier from function-level heuristic xrefs to exact machine instructions. Its
output format is `SHIFT.GhidraVtableXrefInstructionAudit/1`.

The analyzer is intentionally conservative: an instruction becomes a
`heuristic-vtable-address-store-candidate` only when the same instruction both
references a heuristic table address selected by the construction frontier and
contains a structured Ghidra p-code `STORE` operation.

That is still **not** a vptr, constructor, destructor or class proof.

## Inputs

The tool requires:

1. `SHIFT.GhidraConstructionFrontier/1`, produced by
   `build_construction_frontier.py`;
2. `SHIFT.GhidraFunctionInstructions/2`, produced by the targeted Ghidra
   instruction exporter for functions selected by that frontier.

Version-1 instruction exports are rejected because they do not carry structured
p-code opcodes.

Every function in the instruction export must exist in the construction
frontier. Extra functions fail closed instead of being silently interpreted as
construction evidence.

## Exact-reference classification

For each selected instruction the analyzer first intersects the instruction's
Ghidra references with only the heuristic table addresses already associated
with that function by the construction frontier.

If no exact table reference exists, the instruction is ignored.

If a matching reference exists:

- p-code `STORE` -> `heuristic-vtable-address-store-candidate`;
- p-code `LOAD` without `STORE` -> `heuristic-vtable-address-load-candidate`;
- neither -> `heuristic-vtable-address-reference-without-load-store`.

Simple x86 memory operands such as `[ECX]` or `[ESI + 0x8]` are preserved as
syntactic base-register + displacement evidence. Complex addressing expressions
are not reduced.

A matching table-reference instruction with `STORE` but without a simple
register-relative memory operand is emitted as an explicit blocker. This avoids
inventing an object-field offset from indexed, stack-transformed or otherwise
ambiguous addressing.

## Run

```bash
python3 tools/ghidra/analyze_vtable_xref_instructions.py \
  out/physics_vehicle_construction_instructions.jsonl \
  out/physics_vehicle_construction_frontier.json \
  --json-out out/physics_vehicle_vtable_xref_instruction_audit.json \
  --fail-on-blocker
```

The report groups repeated STORE shapes by:

- syntactic base register;
- constant displacement;
- referenced heuristic table address.

Repeated shape is useful object-layout evidence to investigate, but remains
`promoted=false`.

## Safe promotion path

A candidate should only move toward a vptr/object-layout claim after independent
static evidence establishes all of the relevant steps:

1. the referenced read-only table is stronger than a heuristic function-pointer
   array candidate;
2. the exact instruction stores that table address, rather than merely carrying
   another STORE in its p-code expansion;
3. pointer provenance proves the destination register represents the same object
   or subobject across the construction boundary;
4. the destination displacement is reproduced by independent constructor,
   destructor, virtual-call or layout evidence;
5. class identity is tied to strings/factory/registration/callgraph evidence,
   not inferred from table shape alone.

Until then the repository should keep the result as a vtable-address STORE
candidate.

## Evidence boundary

The audit does not prove:

- that a heuristic table is a real class vtable;
- that a STORE destination is a vptr field;
- that the base register is `this` or any object pointer;
- constructor/destructor identity;
- class identity, inheritance or subobject boundaries;
- virtual dispatch target resolution;
- ownership or lifetime semantics;
- object layout beyond the syntactic register + displacement occurrence.

No automatic aliases or function renames are produced.
