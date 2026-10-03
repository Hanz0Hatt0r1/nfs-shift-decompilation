# Process 1 — candidate-table dispatch consistency

The previous block can verify a narrow local fact:

```text
one stable object-pointer value
+ exact literal heuristic-table-address STORE
+ exact table offset
```

That still does not prove a C++ class or virtual dispatch table. This block asks
a separate machine-level question: does the same pointer later load a table
pointer from the same offset and use it in an indirect `CALLIND` slot access?

Tool:

```text
tools/ghidra/analyze_vehicle_candidate_table_dispatch.py
```

Output:

```text
SHIFT.VehicleCandidateTableDispatch/1
```

## Inputs

The analyzer consumes:

```text
raw Ghidra export: binary.json + vtables.json
SHIFT.GhidraFunctionInstructions/2
SHIFT.VehicleVtablePointerAlias/1
```

Example:

```bash
python3 tools/ghidra/analyze_vehicle_candidate_table_dispatch.py \
  out/shift_ghidra_database \
  out/vehicle_ownership_lifecycle_instructions.jsonl \
  out/vehicle_vtable_pointer_alias.json \
  --json-out out/vehicle_candidate_table_dispatch.json
```

## Required machine pattern

A dispatch candidate begins only from a table STORE whose local same-pointer
alias was already `verified` by `SHIFT.VehicleVtablePointerAlias/1`.

The analyzer then looks for:

```text
STORE literal_candidate_table_address -> [object_base + table_offset]
...
MOV table_reg,[object_base + table_offset]
...
CALL [table_reg + slot_displacement]
```

The following gates are independent and all must pass for
`dispatch_consistency_state = verified`.

### Object-pointer continuity

The table load must occur after the verified STORE and use the same object base
register plus exactly the same table offset.

The base-register value must remain stable over the full linear STORE→LOAD
interval using the same fail-closed clobber/control-flow rules as the previous
pointer-alias audit.

### Table-register continuity

The loaded table register must remain stable over the full LOAD→CALL interval.
Calls, branches, returns, partial-register writes, implicit GPR updates, and
unsupported interval instructions prevent verification.

### CALLIND gate

The indirect memory CALL must carry structured Ghidra p-code `CALLIND`.
A textual memory CALL without `CALLIND` remains unresolved.

### Slot alignment/inventory gate

`binary.json` supplies the exact pointer size. The call displacement must be
non-negative and divisible by that pointer size:

```text
slot_index = slot_displacement / pointer_size
```

`vtables.json` must contain that exact slot in the same heuristic candidate
table whose literal address was stored earlier.

The report preserves the candidate slot target/name from `vtables.json` only as
static heuristic-table consistency.

## Evidence boundary

When all gates pass, the report may state:

```text
candidate table address: exact
same object base + table offset: verified
object-base continuity: verified
table-pointer load: verified
table-register continuity: verified
CALLIND: verified
slot index: verified
candidate table has that slot: verified
dispatch consistency: verified
```

It still explicitly keeps:

```text
runtime_target_identity_proven = false
heuristic_table_identity_state = ambiguous
class_identity_proven = false
virtual_dispatch_semantics_proven = false
```

The target recorded in a heuristic table is not proof that the runtime indirect
call actually resolved to that target. The table candidate itself is also not
promoted to a C++ vtable merely because one STORE/LOAD/CALLIND pattern is
consistent with it.

## Why this matters

This block separates two questions that are easy to conflate:

1. **Does machine code use the pointer/table/slot pattern consistently?**
2. **What semantic class/table/virtual method does that pattern represent?**

Only the first question is closed here.

That gives Process 1 stronger lifecycle/dispatch evidence without violating the
fail-closed class-identity policy.

## Blockers

The analyzer reports explicit blockers when a verified table STORE has no
matching later table-pointer load, or when loads exist but no full stable
STORE→LOAD→CALL chain can be closed.

Individual dispatch candidates remain `ambiguous` when:

- `CALLIND` p-code is absent;
- table-register continuity is interrupted;
- slot displacement is misaligned;
- the candidate table has no such slot.

## Fail-closed behavior

The analyzer aborts when:

- input formats drift;
- `vtables.json` is no longer explicitly `heuristic-candidates`;
- pointer size is missing/invalid;
- a verified alias references a table absent from the heuristic inventory;
- the verified STORE instruction is absent from the targeted export.

It never chooses another table or slot by proximity.

## Next promotion gate

A stronger lifecycle/class result should require independent agreement between
several evidence families, for example:

```text
same-pointer exact table STORE
+ same-pointer candidate-table CALLIND slot consistency
+ constructor/reset/destructor topology for the same pointer value
+ RTTI/registration evidence tied to the same table
```

Even then, each semantic promotion should name exactly which independent facts
support it and which remain heuristic.

No original-game execution or runtime capture is used.
