# Process 1 — heuristic table STORE / pointer-value alias audit

Earlier Process 1 layers intentionally keep every `vtables.json` entry and every
`constructors.jsonl` relationship heuristic.  A same-register overlap between a
candidate table STORE and the vehicle-update pointer chain is therefore only a
target-selection hint.

This block strengthens that hint without changing the table's semantic status.

Tool:

```text
tools/ghidra/analyze_vehicle_vtable_pointer_alias.py
```

Output:

```text
SHIFT.VehicleVtablePointerAlias/1
```

## Inputs

The analyzer consumes:

```text
SHIFT.GhidraFunctionInstructions/2
SHIFT.VehiclePointerOriginFrontier/1
SHIFT.VehicleOwnershipInstructionEvidence/1
```

Example:

```bash
python3 tools/ghidra/analyze_vehicle_vtable_pointer_alias.py \
  out/vehicle_ownership_lifecycle_instructions.jsonl \
  out/vehicle_pointer_origin_frontier.json \
  out/vehicle_ownership_instruction_evidence.json \
  --json-out out/vehicle_vtable_pointer_alias.json
```

## Two independent proof gates

For every vtable-store overlap selected by the pointer-origin report, the
analyzer evaluates two independent properties.

### 1. Exact candidate-table address STORE shape

The raw instruction must be a simple `MOV` with structured p-code `STORE`:

```text
MOV [base + displacement], literal_address
```

The literal source address must exactly equal one of the heuristic table
addresses referenced by the same instruction.

Only then is the narrow instruction shape marked `verified`.

Symbolic/non-literal source text is deliberately not guessed from a nearby data
reference. A reference plus STORE p-code does not prove which operand supplied
the stored value.

### 2. Local base-register value continuity

The table STORE and the receiver/base-source instruction must use the same
textual 32-bit base register. The analyzer scans every instruction on the
linear interval between them.

Continuity becomes `verified` only if the scan finds no:

- `CALL` / `CALLIND`;
- conditional or unconditional branch;
- return;
- explicit write to the base register;
- partial-register write such as `SI` when the tracked register is `ESI`;
- known implicit GPR update such as x86 string-index operations, stack updates,
  `CPUID`, `RDTSC`, one-operand multiply/divide, etc.;
- `XCHG`/`XADD` write involving the base register;
- unsupported interval instruction for which the analyzer has no fail-closed
  GPR-write rule.

Unknown instructions are not crossed optimistically.

## Combined result

When both gates are verified and the STORE destination uses the receiver-source
base register, the report may state:

```text
same_pointer_table_store_state = verified
```

This means only:

```text
the same locally stable register value
was used as the memory base
for an exact literal heuristic-table-address STORE
and for the later/earlier receiver-source memory use
```

It still does **not** mean the table is a proven C++ vtable or the pointer is a
proven vehicle/class instance.

## Offset-zero result

If the verified STORE is exactly:

```text
[base + 0]
```

the report additionally exposes:

```text
same_pointer_offset_zero_table_store_verified = true
```

That is useful layout evidence, but the following remain false:

```text
vptr_semantics_proven
class_identity_proven
constructor_role_proven
destructor_role_proven
owner_identity_proven
```

An offset-zero candidate-table STORE is not promoted to vptr/class semantics
while the source table itself remains a heuristic vtable candidate.

A non-zero STORE can still have verified same-pointer continuity and an exact
literal table address. The offset is preserved exactly, but no subobject/vptr
meaning is assigned.

## Why this is stronger than the previous overlap

The previous layer could only say:

```text
same textual base register appears at both instructions
```

This block additionally proves that no accepted instruction on the linear
interval changes that register value and that the STORE source is the exact
candidate-table address.

Thus it closes a local pointer-value alias boundary while keeping semantic table
identity separate.

## Remaining promotion gate

A future lifecycle/class contract needs independent evidence that the candidate
table is actually a class dispatch table and that the STORE has lifecycle
meaning. Suitable independent evidence can include:

- exact constructor/destructor call topology;
- exact initialization/reset ordering;
- RTTI/class-registration evidence tied to the same table;
- multiple virtual callsites whose proven slot targets match the same table;
- the same pointer-value provenance reaching those callsites.

Only then should a semantic class/vptr role be considered for promotion.

## Fail-closed behavior

The analyzer aborts when:

- input formats drift;
- pointer and owner-instruction anchors disagree;
- a pointer-origin overlap has no matching instruction-level candidate;
- the required raw STORE or receiver-source instruction is missing.

It returns `ambiguous` rather than guessing when:

- the STORE source is not an exact literal address;
- the literal address disagrees with the referenced candidate table;
- pointer continuity crosses a control-flow/call/clobber boundary;
- interval instruction semantics are unsupported.

No original-game execution or runtime capture is used.
