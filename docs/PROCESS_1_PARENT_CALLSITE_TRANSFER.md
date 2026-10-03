# Process 1 — parent callsite register transfer

`SHIFT.VehiclePointerOriginFrontier/1` can end at a child function-entry
register and emit exact direct parents for the next static pass. This block
closes that one interprocedural boundary without assigning object semantics.

Tool:

```text
tools/ghidra/analyze_vehicle_parent_callsite_transfer.py
```

Output:

```text
SHIFT.VehicleParentCallsiteTransfer/1
```

## Purpose

Given a child pointer-origin boundary such as:

```text
child entry ECX
  -> local ESI
  -> [ESI + 0x40]
  -> receiver passed to FUN_007155e9
```

the analyzer proves which exact parent callsite reaches the child and what
source shape produced that same architectural register immediately before the
call.

This is a value-transfer proof only. It does not prove that the transferred
value is a vehicle, manager, owner, `this`, BODY, or any other semantic object.

## Inputs

The analyzer consumes:

- the raw Ghidra export containing `functions.jsonl` and `callgraph.jsonl`;
- a targeted `SHIFT.GhidraFunctionInstructions/2` export containing the parent
  functions selected by the pointer-origin frontier;
- `SHIFT.VehiclePointerOriginFrontier/1`.

Example:

```bash
python3 tools/ghidra/analyze_vehicle_parent_callsite_transfer.py \
  out/shift_ghidra_database \
  out/vehicle_parent_callsite_instructions.jsonl \
  out/vehicle_pointer_origin_frontier.json \
  --json-out out/vehicle_parent_callsite_transfer.json \
  --targets-out out/vehicle_parent_callsite_next_targets.txt
```

## Exact parent set gate

For every child entry-register boundary, the report reopens raw
`callgraph.jsonl` and recomputes the direct incoming parent set.

That set must exactly match `direct_incoming_callers` frozen by the previous
pointer-origin report. Any added, removed, or changed parent aborts the
analysis.

This prevents an older summary from silently surviving a newer static export.

## Exact callsite gate

Every raw parent→child edge contributes one exact call instruction address.
The targeted instruction export must contain that exact instruction and satisfy:

```text
instruction.flows contains child
AND
structured p-code contains CALL
```

The callgraph edge, flow and p-code therefore cross-check the same static
transfer site independently.

## Architectural register transfer

For ordinary 32-bit x86 near `CALL`, the general-purpose register values other
than `ESP` immediately before the instruction are the same values observed in
those registers at callee entry. The analyzer records that narrow architectural
boundary as `verified`.

This does not depend on whether the register is caller-saved or callee-saved.
Those conventions govern what a callee may preserve for its caller after the
call, not the value present at callee entry.

`ESP` is explicitly excluded from unchanged transfer because the `CALL` itself
pushes the return address before control reaches the callee. An `ESP` entry
boundary is therefore `ambiguous` in this layer.

## Parent-side provenance

After the register-transfer boundary is established, the analyzer reuses the
same conservative local origin rules as the pointer-origin frontier.

Examples:

```text
MOV ECX,[ESI+0x20]
CALL child
```

can produce a verified parent-side syntactic source:

```text
ECX <- [ESI+0x20]
```

while:

```text
MOV ECX,ESI
CALL other_function
CALL child
```

keeps the transfer into `child` verified but marks the older ECX source
`ambiguous`, because the intervening call is a provenance barrier.

The transfer fact and the origin fact therefore have separate evidence states.

## Recursive frontier extension

If the parent-side trace itself terminates at a parent function-entry register,
the analyzer looks up the parent's exact raw direct incoming callers and emits
them as the next instruction-export targets.

The resulting progression is mechanical:

```text
child entry register
<- exact parent register at exact CALL
<- parent local source or parent entry register
<- next parent callsite when needed
```

A direct parent remains only an execution predecessor. It is not automatically
an owner or scheduler.

## Fail-closed boundaries

The analyzer aborts when:

- the pointer-origin input format drifts;
- the raw direct parent set differs from the previous frontier;
- a required parent is absent from the targeted instruction export;
- the exact call instruction disappears;
- the call instruction no longer flows to the expected child;
- the direct edge lacks structured `CALL` p-code;
- an unsupported entry register is encountered.

Local provenance still stops at calls, branches, returns, unsupported register
writes, complex memory forms, or malformed instruction evidence.

## Evidence policy

Promoted by this layer:

- exact raw parent→child direct callgraph edges;
- exact parent call instruction addresses;
- matching Ghidra flow plus p-code `CALL`;
- architectural continuity of non-`ESP` general-purpose register values across
  that near-call boundary;
- conservative parent-side syntactic register origin when locally provable.

Not promoted:

- object identity;
- owner identity;
- class identity;
- `this` identity;
- constructor/destructor role;
- field names or physical units;
- input/control ownership;
- rendered-frame cadence.

## Next static block

Repeated parent-callsite reports can now be composed into a pointer-value chain
whose nodes are exact `(function, instruction, register)` locations and whose
edges are one of:

```text
local MOV/LEA origin
exact CALL-boundary register transfer
register-relative load/address source
function-entry boundary
```

The next useful automation is a closure graph that deduplicates these chains,
detects cycles/barriers, and joins completed pointer identities to independent
allocation/vtable/lifecycle evidence only when exact pointer provenance agrees.

No original-game execution or runtime capture is used.
